from rest_framework import status
from rest_framework.response import Response


def to_mds_error_response(validation_error):
    """Turn DRF validation errors to what the spec is saying.

    We lose details in the process.
    """
    # Usual codes from ValidationError
    codes = {"invalid": [], "required": []}
    try:
        # The field is always "data" as it's the only field in the serializer
        details = validation_error.get_full_details()["data"][0]
        for field_name, error_details in details.items():
            for error_detail in error_details:
                if error_detail["message"].code == "required":
                    codes["required"].append(field_name)
                else:
                    codes["invalid"].append(field_name)
        if codes["required"]:
            return Response(
                {
                    "error": "missing_param",
                    "error_description": "A required parameter is missing.",
                    "error_details": codes["required"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        elif codes["invalid"]:
            return Response(
                {
                    "error": "bad_param",
                    "error_description": "A validation error occurred.",
                    "error_details": codes["invalid"],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        # When we really don't know how to translate validation errors
        raise ValueError()
    except (KeyError, ValueError):
        return Response(
            {
                "error": "invalid_data",
                "error_description": "None of the provided data was valid.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    except Exception:
        # If we're still left with an error we can't translate, just raise it
        raise validation_error
