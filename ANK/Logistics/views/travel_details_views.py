from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from Logistics.models.travel_details_models import TravelDetail
from Logistics.serializers.travel_details_serializers import TravelDetailSerializer
from utils.swagger import (
    document_api_view,
    doc_list,
    doc_create,
    doc_retrieve,
    doc_update,
    doc_destroy,
    query_param,
)


@document_api_view(
    {
        "get": doc_list(
            response=TravelDetailSerializer(many=True),
            parameters=[
                query_param(
                    "event_registration",
                    "uuid",
                    False,
                    "Filter by event registration ID",
                ),
                query_param(
                    "session_registration",
                    "uuid",
                    False,
                    "Filter by session registration ID",
                ),
                query_param("arrival", "str", False, "Filter by arrival method"),
                query_param(
                    "return_travel", "bool", False, "Filter by return travel flag"
                ),
            ],
            description="List all travel details",
            tags=["Travel Details"],
        ),
        "post": doc_create(
            request=TravelDetailSerializer,
            response=TravelDetailSerializer,
            description="Create a new travel detail",
            tags=["Travel Details"],
        ),
    }
)
class TravelDetailList(APIView):
    def get(self, request):
        try:
            qs = TravelDetail.objects.all()
            return Response(TravelDetailSerializer(qs, many=True).data)
        except Exception as e:
            return Response(
                {"detail": "Error fetching travel details", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def post(self, request):
        try:
            ser = TravelDetailSerializer(data=request.data)
            ser.is_valid(raise_exception=True)
            td = ser.save()
            return Response(
                TravelDetailSerializer(td).data, status=status.HTTP_201_CREATED
            )
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": "Error creating travel detail", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


@document_api_view(
    {
        "get": doc_retrieve(
            response=TravelDetailSerializer,
            description="Retrieve a travel detail by ID",
            tags=["Travel Details"],
        ),
        "put": doc_update(
            request=TravelDetailSerializer,
            response=TravelDetailSerializer,
            description="Update a travel detail by ID",
            tags=["Travel Details"],
        ),
        "delete": doc_destroy(
            description="Delete a travel detail by ID", tags=["Travel Details"]
        ),
    }
)
class TravelDetailDetail(APIView):
    def get(self, request, pk):
        try:
            td = get_object_or_404(TravelDetail, pk=pk)
            return Response(TravelDetailSerializer(td).data)
        except Exception as e:
            return Response(
                {"detail": "Error fetching travel detail", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def put(self, request, pk):
        try:
            td = get_object_or_404(TravelDetail, pk=pk)
            ser = TravelDetailSerializer(td, data=request.data, partial=True)
            ser.is_valid(raise_exception=True)
            td = ser.save()
            return Response(TravelDetailSerializer(td).data)
        except ValidationError as ve:
            return Response(ve.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"detail": "Error updating travel detail", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def delete(self, request, pk):
        try:
            td = get_object_or_404(TravelDetail, pk=pk)
            td.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response(
                {"detail": "Error deleting travel detail", "error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
