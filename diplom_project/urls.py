"""
URL configuration for diplom_drf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.authtoken.views import obtain_auth_token

from orders.views import UserViewSet, UserCreateViewSet, ShopCreate, ShopUpdate, \
    ShopDestroy, ContactCreate, ContactUpdate, ListProductView, ListProductDateView, ListCategoryView, \
    ListShopView, OrderItemCreate, OrderProcessing, OrderAdminProcessing

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register('user', UserViewSet)
router.register('usercreate', UserCreateViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)), # Роут для работы с пользователем

    # Пути для работы с контактом
    path('api/contact/create/', ContactCreate.as_view()),
    path('api/contact/update/<int:pk>/', ContactUpdate.as_view()),

    # Пути для создания/удаления магазина
    path('api/shop/create/', ShopCreate.as_view()),
    path('api/shop/all/', ShopCreate.as_view()),
    path('api/shop/update/<int:pk>/', ShopUpdate.as_view()),
    path('api/shop/delete/<int:pk>/', ShopDestroy.as_view()),

    # Пути для получения и фильтрации товара
    path('api/product/list/', ListProductView.as_view()), # Список товара
    path('api/product/list/date/', ListProductDateView.as_view()), # Фильтр по дате
    path('api/category/list/', ListCategoryView.as_view()), # Фильтр по категориям
    path('api/shop/list/', ListShopView.as_view()), # Фильтр по магазинам

    # Пути для создания заказа
    path('api/basket/list/', OrderItemCreate.as_view()), # Просмотр корзины
    path('api/basket/add/', OrderItemCreate.as_view()),
    path('api/basket/delete/<int:pk>/', OrderItemCreate.as_view()),

    # Пути для обработки заказа (пользователь)
    path('api/order/processing/', OrderProcessing.as_view()),  # Передача заказа в обработку пользователем
    path('api/order/list/', OrderProcessing.as_view()), # Просмотр состояния заказа пользователем

    # Пути для обработки заказа (админ)
    path('api/order/admin/list/<int:pk>/', OrderAdminProcessing.as_view()),  # Просмотр заказа по номеру заказа
    path('api/order/admin/processing/', OrderAdminProcessing.as_view()),  # Запуск заказа в доставку

]