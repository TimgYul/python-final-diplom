from django_filters import rest_framework as filters, DateFromToRangeFilter

from orders.models import ProductInfo


class ProductFilter(filters.FilterSet):
    """Фильтры для продуктов."""
    time_create = DateFromToRangeFilter()

    class Meta:
        model = ProductInfo
        fields = ['time_create',]