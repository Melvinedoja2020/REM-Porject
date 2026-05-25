from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view

from core.applications.users.api.v1.serializers import (
    AgentDocumentVerificationResponseSerializer,
)
from core.applications.users.api.v1.serializers import (
    AgentDocumentVerificationSerializer,
)
from core.applications.users.api.v1.serializers import (
    AgentProfessionalDetailsResponseSerializer,
)
from core.applications.users.api.v1.serializers import (
    AgentProfessionalDetailsSerializer,
)
from core.applications.users.api.v1.serializers import AgentSignupSerializer
from core.applications.users.api.v1.serializers import CustomerSignupSerializer

user_schema = extend_schema_view(

    # ------------------------------------------------------------------
    # CUSTOMER SIGNUP
    # ------------------------------------------------------------------

    customer_signup=extend_schema(
        summary="Customer signup",
        description="""
Create a customer account.

### Flow
1. User submits signup form
2. Account is created with `is_active=False`
3. Activation email is sent
4. Frontend redirects user to email verification screen

### Authentication
No authentication required.

### Supported auth providers
- EMAIL
- PHONE
- GOOGLE (future support)

### Notes
- Email must be unique
- Phone number must be unique
- Password + re_password must match
""",
        request=CustomerSignupSerializer,
        responses={
            201: OpenApiResponse(
                description="Customer account created successfully.",
            ),
            400: OpenApiResponse(
                description="Validation error.",
            ),
        },
        examples=[
            OpenApiExample(
                "Email Signup",
                request_only=True,
                value={
                    "first_name": "Douglas",
                    "last_name": "Chiemela",
                    "email": "douglas@example.com",
                    "password": "StrongPass123!",
                    "re_password": "StrongPass123!",
                    "auth_provider": "EMAIL",
                },
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # AGENT SIGNUP
    # ------------------------------------------------------------------

    agent_signup=extend_schema(
        summary="Agent signup - onboarding step 1",
        description="""
Creates an agent account and starts the onboarding flow.

### Flow
1. Agent account is created
2. Activation email is sent
3. API returns onboarding_token
4. Frontend stores onboarding_token securely
5. Frontend redirects to professional details screen

### Authentication
No authentication required.

### Important
The `onboarding_token` returned from this endpoint is required for:
- agent_professional_details
- agent_document_verification

### Notes
- Account is initially inactive
- User must activate email before completing onboarding
""",
        request=AgentSignupSerializer,
        responses={
            201: OpenApiResponse(
                description="Agent account created successfully.",
            ),
            400: OpenApiResponse(
                description="Validation error.",
            ),
        },
        examples=[
            OpenApiExample(
                "Agent Signup Example",
                request_only=True,
                value={
                    "first_name": "Douglas",
                    "last_name": "Chiemela",
                    "email": "douglas@example.com",
                    "password": "StrongPass123!",
                    "re_password": "StrongPass123!",
                    "auth_provider": "EMAIL",
                    "gender": "MALE",
                },
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # AGENT PROFESSIONAL DETAILS
    # ------------------------------------------------------------------

    agent_professional_details=extend_schema(
        summary="Agent onboarding - professional details (step 2)",
        description="""
Second onboarding step for agents.

Updates the agent's professional/business information.

### Authentication
Uses `onboarding_token` instead of JWT authentication.

### Required fields
For `REAL_ESTATE_AGENT`:
- license_number is required

For `PROPERTY_MANAGER`:
- license_number is optional

### Frontend behavior
On success:
- store response
- redirect user to document upload screen
""",
        request=AgentProfessionalDetailsSerializer,
        responses={
            200: AgentProfessionalDetailsResponseSerializer,
            400: OpenApiResponse(
                description="Validation error.",
            ),
        },
        examples=[
            OpenApiExample(
                "Real Estate Agent",
                request_only=True,
                value={
                    "onboarding_token": "token_here",
                    "agent_type": "REAL_ESTATE_AGENT",
                    "office_address": "12 Aba Road",
                    "years_of_experience": 5,
                    "license_number": "LIC-12345",
                    "office_location": "Port Harcourt",
                },
            ),
            OpenApiExample(
                "Property Manager",
                request_only=True,
                value={
                    "onboarding_token": "token_here",
                    "agent_type": "PROPERTY_MANAGER",
                    "office_address": "12 Aba Road",
                    "years_of_experience": 3,
                    "office_location": "Port Harcourt",
                },
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # AGENT DOCUMENT VERIFICATION
    # ------------------------------------------------------------------

    agent_document_verification=extend_schema(
        summary="Agent onboarding - document verification (step 3)",
        description="""
Final onboarding step for agents.

Uploads verification documents and submits account for admin review.

### Content Type
multipart/form-data

### Authentication
Uses `onboarding_token` instead of JWT authentication.

### File Uploads
Supported fields:
- license_document
- profile_picture

### Frontend Requirements
Send request as multipart/form-data.

### On Success
- verification_status becomes SUBMITTED
- account enters admin review stage
- frontend should redirect to onboarding completion screen
""",
        request=AgentDocumentVerificationSerializer,
        responses={
            200: AgentDocumentVerificationResponseSerializer,
            400: OpenApiResponse(
                description="Validation error.",
            ),
        },
        examples=[
            OpenApiExample(
                "Multipart Form Example",
                request_only=True,
                value={
                    "onboarding_token": "token_here",
                    "license_document": "<file>",
                    "profile_picture": "<image>",
                },
            ),
        ],
    ),

    # ------------------------------------------------------------------
    # ACCOUNT ACTIVATION
    # ------------------------------------------------------------------

    activation=extend_schema(
        summary="Activate account",
        description="""
Activates a user account using:
- email
- activation token

### Flow
Frontend usually opens this endpoint after user clicks activation link from email.

### Result
- account becomes active
- JWT tokens are returned
- frontend logs user in immediately
""",
    ),

    resend_activation=extend_schema(
        summary="Resend activation email",
        description="""
Resends account activation email.

Used when user did not receive activation email.
""",
    ),

    reset_password=extend_schema(
        summary="Request password reset",
        description="""
Sends password reset email to user.
""",
    ),

    reset_password_confirm=extend_schema(
        summary="Confirm password reset",
        description="""
Completes password reset using:
- email
- token
- new password
""",
    ),

    logout=extend_schema(
        summary="Logout user",
        description="""
Logs out authenticated user.

JWT token should also be removed from frontend storage.
""",

    ),

    me=extend_schema(
        summary="Current authenticated user",
        description="""
Returns currently authenticated user profile.
""",

    ),

    get_by_email=extend_schema(
        summary="Get user by email",
        description="""
Retrieve user details using email address.
""",

    ),
)
