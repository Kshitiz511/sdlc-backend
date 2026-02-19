from rest_framework.decorators import api_view
from rest_framework.response import Response
from .foundry_service import generate_brd_tap


@api_view(["POST"])
def generate_document(request):
    prompt = request.data.get("prompt", "")

    if not prompt:
        return Response({"error": "Prompt is required"}, status=400)

    try:
        result = generate_brd_tap(prompt)
        print("DJANGO RESPONSE →", result)
        return Response(result)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
