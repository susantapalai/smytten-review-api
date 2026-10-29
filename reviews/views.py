from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Review
from .serializers import ProductSerializer, ReviewSerializer
from .services import summarize_reviews


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("-created_at")
    serializer_class = ProductSerializer

    @action(detail=True, methods=["post"], url_path="summary",
            permission_classes=[IsAuthenticated])
    def summary(self, request, pk=None):
        product = self.get_object()
        reviews = product.reviews.all()
        if not reviews.exists():
            return Response({"detail": "No reviews for this product yet."},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(summarize_reviews(product, reviews))


class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer

    def get_queryset(self):
        qs = Review.objects.select_related("user", "product").order_by("-created_at")
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
