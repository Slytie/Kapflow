from __future__ import annotations

import os
from typing import Any, Mapping

from .dependencies import (
    RequestContext,
    PrincipalResolver,
    normalize_actor_roles,
    normalize_actor_type,
)
from .errors import ApiError

SHARED_ENV_JWT_ISSUER_ENV = "ONETRUTH_SHARED_ENV_JWT_ISSUER"
SHARED_ENV_JWT_AUDIENCE_ENV = "ONETRUTH_SHARED_ENV_JWT_AUDIENCE"
SHARED_ENV_JWT_PUBLIC_KEY_PEM_ENV = "ONETRUTH_SHARED_ENV_JWT_PUBLIC_KEY_PEM"
_AUTHORIZATION_HEADER = "authorization"
_JWT_ALGORITHMS = ("RS256",)
_SHARED_ENV_ERROR_CODE = "invalid_attested_identity"
_MISSING_BEARER_TOKEN_CODE = "missing_bearer_token"
_PYJWT_IMPORT_HINT = (
    "PyJWT is required for the shared_env JWT principal resolver. "
    "Install with `python3 -m pip install -e .[api]`."
)


def shared_env_jwt_principal_resolver_from_env() -> PrincipalResolver | None:
    issuer = _configured_env(SHARED_ENV_JWT_ISSUER_ENV)
    audience = _configured_env(SHARED_ENV_JWT_AUDIENCE_ENV)
    public_key_pem = _configured_env(SHARED_ENV_JWT_PUBLIC_KEY_PEM_ENV)
    if issuer is None or audience is None or public_key_pem is None:
        return None
    _pyjwt_module()
    return build_shared_env_jwt_principal_resolver(
        issuer=issuer,
        audience=audience,
        public_key_pem=public_key_pem,
    )


def build_shared_env_jwt_principal_resolver(
    *,
    issuer: str,
    audience: str,
    public_key_pem: str,
) -> PrincipalResolver:
    def resolve(headers: Mapping[str, str]) -> RequestContext:
        token = _extract_bearer_token(headers)
        claims = _decode_jwt(
            token=token,
            issuer=issuer,
            audience=audience,
            public_key_pem=public_key_pem,
        )
        return RequestContext(
            tenant_id=_required_claim_string(claims, "tenant_id"),
            domain_id=_required_claim_string(claims, "domain_id"),
            actor_id=_required_claim_string(claims, "sub"),
            actor_type=normalize_actor_type(
                claims.get("actor_type"),
                status_code=401,
                code=_SHARED_ENV_ERROR_CODE,
                source="jwt claim actor_type",
            ),
            actor_roles=normalize_actor_roles(
                claims.get("actor_roles"),
                status_code=401,
                code=_SHARED_ENV_ERROR_CODE,
                source="jwt claim actor_roles",
            ),
        )

    return resolve


def _configured_env(name: str) -> str | None:
    raw_value = os.environ.get(name)
    if raw_value is None:
        return None
    value = raw_value.strip()
    return value or None


def _extract_bearer_token(headers: Mapping[str, str]) -> str:
    raw_authorization = headers.get(_AUTHORIZATION_HEADER)
    if raw_authorization is None or not raw_authorization.strip():
        raise ApiError(
            status_code=401,
            code=_MISSING_BEARER_TOKEN_CODE,
            message="missing Authorization bearer token",
            details={"boundary_profile": "shared_env"},
        )

    parts = raw_authorization.strip().split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1].strip():
        raise ApiError(
            status_code=401,
            code=_MISSING_BEARER_TOKEN_CODE,
            message="Authorization header must use the Bearer scheme",
            details={"boundary_profile": "shared_env"},
        )
    return parts[1].strip()


def _decode_jwt(
    *,
    token: str,
    issuer: str,
    audience: str,
    public_key_pem: str,
) -> dict[str, Any]:
    jwt = _pyjwt_module()
    try:
        claims = jwt.decode(
            token,
            public_key_pem,
            algorithms=list(_JWT_ALGORITHMS),
            issuer=issuer,
            audience=audience,
            options={
                "require": [
                    "aud",
                    "domain_id",
                    "exp",
                    "iss",
                    "sub",
                    "tenant_id",
                    "actor_type",
                    "actor_roles",
                ]
            },
        )
    except jwt.PyJWTError as exc:
        raise ApiError(
            status_code=401,
            code=_SHARED_ENV_ERROR_CODE,
            message="bearer token could not be validated",
            details={
                "boundary_profile": "shared_env",
                "reason": exc.__class__.__name__,
            },
        ) from exc

    if not isinstance(claims, dict):
        raise ApiError(
            status_code=401,
            code=_SHARED_ENV_ERROR_CODE,
            message="bearer token claims must decode to a JSON object",
            details={"boundary_profile": "shared_env"},
        )
    return claims


def _required_claim_string(claims: Mapping[str, Any], claim_name: str) -> str:
    raw_value = claims.get(claim_name)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise ApiError(
            status_code=401,
            code=_SHARED_ENV_ERROR_CODE,
            message=f"required JWT claim {claim_name} must be a non-empty string",
            details={"boundary_profile": "shared_env", "claim": claim_name},
        )
    return raw_value.strip()


def _pyjwt_module():
    try:
        import jwt
    except ImportError as exc:
        raise RuntimeError(_PYJWT_IMPORT_HINT) from exc
    return jwt
