from drf_spectacular.utils import extend_schema, OpenApiExample


# ------------------------------------------------------------------
# JWT LOGIN
# ------------------------------------------------------------------

JWT_LOGIN_SCHEMA = extend_schema(
    tags=["Authentication"],
    summary="Obtain JWT Token Pair",
    description="""
Authenticate a user using email/phone and password.

Returns a JWT token pair used for authenticated requests:
- access token (short-lived)
- refresh token (long-lived)

This is the primary authentication entry point for the API.
    """,
    request={
        "type": "object",
        "properties": {
            "email": {
                "type": "string",
                "description": "User email or phone number"
            },
            "password": {
                "type": "string",
                "description": "User account password"
            },
        },
        "required": ["password"],
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "access": {
                    "type": "string",
                    "description": "JWT access token"
                },
                "refresh": {
                    "type": "string",
                    "description": "JWT refresh token"
                },
            },
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "string",
                    "example": "No active account found with the given credentials"
                }
            },
        },
    },
    examples=[
        OpenApiExample(
            "Login Request",
            value={
                "email": "user@example.com",
                "password": "securePassword123"
            },
            request_only=True,
        ),
        OpenApiExample(
            "Login Response",
            value={
                "access": "eyJhbGciOiJIUzI1NiIs...",
                "refresh": "eyJhbGciOiJIUzI1NiIs..."
            },
            response_only=True,
        ),
    ],
)


# ------------------------------------------------------------------
# JWT VERIFY
# ------------------------------------------------------------------

JWT_VERIFY_SCHEMA = extend_schema(
    tags=["Authentication"],
    summary="Verify JWT Token",
    description="""
Validates a JWT token.

Used to:
- Check if a token is valid
- Confirm authentication state
- Debug expired or invalid tokens
    """,
    request={
        "type": "object",
        "properties": {
            "token": {
                "type": "string",
                "description": "JWT access or refresh token"
            }
        },
        "required": ["token"],
    },
    responses={
        200: {},  # empty response = valid token
        401: {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "string",
                    "example": "Token is invalid or expired"
                }
            },
        },
    },
    examples=[
        OpenApiExample(
            "Verify Request",
            value={
                "token": "eyJhbGciOiJIUzI1NiIs..."
            },
            request_only=True,
        )
    ],
)


# ------------------------------------------------------------------
# JWT REFRESH
# ------------------------------------------------------------------

JWT_REFRESH_SCHEMA = extend_schema(
    tags=["Authentication"],
    summary="Refresh JWT Access Token",
    description="""
Generate a new access token using a valid refresh token.

This endpoint:
- Extends user session without re-login
- Keeps authentication secure and stateless

Refresh tokens may expire or be blacklisted.
    """,
    request={
        "type": "object",
        "properties": {
            "refresh": {
                "type": "string",
                "description": "Valid refresh token issued during login"
            }
        },
        "required": ["refresh"],
    },
    responses={
        200: {
            "type": "object",
            "properties": {
                "access": {
                    "type": "string",
                    "description": "New JWT access token"
                }
            },
        },
        401: {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "string",
                    "example": "Token is invalid or expired"
                }
            },
        },
    },
    examples=[
        OpenApiExample(
            "Refresh Request",
            value={
                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            request_only=True,
        ),
        OpenApiExample(
            "Refresh Response",
            value={
                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            },
            response_only=True,
        ),
    ],
)
