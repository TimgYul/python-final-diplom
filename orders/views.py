from django.http import JsonResponse
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.generics import ListAPIView, ListCreateAPIView, UpdateAPIView
from django.contrib.auth.models import User
from orders.filters import ProductFilter

from orders.permissions import get_username, IsOwner
from orders.signal import order_user_create_send_mail, order_seller_confirm_send_mail, order_buyer_confirm_send_mail

from .serializers import UserSerializer, ShopSerializer, ContactSerializer, ProductSerializer, CategorySerializers, \
    ShopSerializersFORFilters, OrderSerializer, OrderProcessingSerializer
from orders.models import Shop, Contact, Category, Product, ProductInfo, OrderItem, Order
from django.core.exceptions import ObjectDoesNotExist

from rest_framework import viewsets, mixins


# Работа с пользователем

class UserCreateViewSet(mixins.CreateModelMixin,
                   viewsets.GenericViewSet):
    """Создание пользователя"""
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserViewSet(mixins.RetrieveModelMixin,
                   mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,
                   viewsets.GenericViewSet):
    """Взаимдействие с пользователем"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated, IsOwner)


# class UserVkViewSet(APIView):н
#     """Сюда осуществляется редирект после аутентификации в VK.
#     я так и не разобрался как вытащить из запроса(сессии) имя пользователя под которым прошла регистрация."""

#     def get(self, request, *args, **kwargs):
#         # print(request.auth.key)
#         return JsonResponse({'Answer': 'Thank you for using the our service!'})


# Работа с контактом

class ContactCreate(ListCreateAPIView):
    """Создание контакта"""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = (IsAuthenticated,)

class ContactUpdate(UpdateAPIView):
    """Обновление контакта"""
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = (IsAuthenticated,)


# Работа с магазином

class ShopCreate(ListCreateAPIView):
    """Создание магазина, заполнение таблиц из прайса"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = (IsAuthenticated,)

class ShopUpdate(UpdateAPIView):
    """Обновление магазина"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = (IsAuthenticated, IsOwner)

class ShopDestroy(APIView):
    """Удаление магазина и всех товаров"""

    permission_classes = (IsAuthenticated,  IsOwner)

    def delete(self, request, pk=None):
        try:
            shop = Shop.objects.only('id').get(id=pk) # Здесь берутся значения определенного столбца
            # shop = Shop.objects.select_related('user').get(id=pk)
            categories = Category.objects.only('id').filter(shops=shop.id)
            # categories = Category.objects.prefetch_related('shops').filter(shops=shop.id)
            for cat in categories:
                # prod = Product.objects.select_related('category').filter(category_id=cat.id)
                prod = Product.objects.only('category_id').filter(category_id=cat.id)
                prod.delete()
            categories.delete()
            shop.delete()
            return Response({'Answer': "The store has been deleted!"})
        except ObjectDoesNotExist:
            return Response({"Answer": "The store not found!"})

# Класс для работы с заказом

class OrderItemCreate(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """ Просмотр корзины пользователя """
        user_id = get_username(request)
        user = User.objects.get(id=user_id)
        contact = Contact.objects.values('user_id','phone').get(user_id=user_id) # Здесь берутся значения по определенным столбцам

        order_dict = {}
        total_cost = 0

        orders = Order.objects.values('id','user_id','state').filter(user_id=user_id, state='basket') # Здесь берутся значения по определенным столбцам

        for order in orders:
            orderitem = OrderItem.objects.get(order_id=order['id'])
            products = ProductInfo.objects.values('external_id','price_rrc','model').filter(id=orderitem.product_info_id) # Здесь берутся значения по определенным столбцам

            for product in products:
                order_dict[order['id']] = f"external_id:{product['external_id']}, model:{product['model']}, price:{product['price_rrc']}, quantity:{orderitem.quantity}, total_price: {product['price_rrc']*orderitem.quantity} rubles."
                total_cost += product['price_rrc']*orderitem.quantity

        order_dict['total_cost']=f'{total_cost} rubles.'

        return JsonResponse({'user': user.username, 'phone': contact['phone'], 'orders':order_dict})


    def post(self, request, *args, **kwargs):
        """ Добавление заказа в корзину """

        user_id = get_username(request)
        contact = Contact.objects.get(user_id=user_id)

        serializer = OrderSerializer(data=request.data)

        if serializer.is_valid():
            try:
                product_info = ProductInfo.objects.get(external_id=serializer.data['external_id'])
                shop = Shop.objects.get(id=product_info.shop_id)
                if shop.name != serializer.data['shop']:
                    return JsonResponse({'Error': 'The store not found!'})
                else:
                    if shop.state == True: # Проверка активен ли магазин
                        order = Order.objects.create(state='basket', contact_id=contact.id, user_id=user_id)
                        OrderItem.objects.create(quantity=serializer.data['quantity'], order_id=order.id, product_info_id=product_info.id)
                        return Response({'Answer': 'You order is added, go to basket'})
                    else:
                        return JsonResponse({'Error': 'The store is deactivated!'})
            except ObjectDoesNotExist:
                return JsonResponse({"Error": "The product not found!"})
        return JsonResponse({'Error': serializer.errors})


    def delete(self, request, pk, format=None):
        """ Удаление заказа из корзины"""
        user_id = get_username(request)

        try:
            order = Order.objects.get(id=pk, user_id=user_id, state='basket')
            OrderItem.objects.get(order_id=order.id).delete()
            order.delete()
            return JsonResponse({'Answer': 'Order deleted!'})
        except ObjectDoesNotExist:
            return JsonResponse({"Error": "The order not found, or you not Owner!"})


#класс для пользвателя

class OrderProcessing(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """ Просмотр заказов """
        user_id = get_username(request)
        user = User.objects.get(id=user_id)

        order_dict = {}

        orders = Order.objects.filter(user_id=user_id) & Order.objects.exclude(state='basket')
        for order in orders:
            orderitem = OrderItem.objects.get(order_id=order.id)
            products = ProductInfo.objects.filter(id=orderitem.product_info_id)
            for product in products:
                order_dict[order.id] = f'Status:{order.state}, model:{product.model},  quantity:{orderitem.quantity}.'

        return Response({'first_name': user.first_name, 'last_name': user.last_name, 'orders':order_dict})


    def post(self, request, *args, **kwargs):
        """ Запуск заказа в обработку"""

        user_id = get_username(request)
        user = User.objects.get(id=user_id)

        serializer = OrderProcessingSerializer(data=request.data)

        if serializer.is_valid():

            if serializer.data['state'] == 'Confirmed':
                try:
                    orders_count = Order.objects.filter(user_id=user_id, state='basket').count()
                    if orders_count == 0:
                       return JsonResponse({'Error': 'No orders!'})
                    orders = Order.objects.filter(user_id=user_id, state='basket')
                    orders_list = []
                    for order in orders:
                        orders_list.append(order.id)
                        order_items = OrderItem.objects.filter(order_id=order.id)
                        for order_item in order_items:
                            product_info = ProductInfo.objects.get(id=order_item.product_info_id)
                            value = product_info.quantity - order_item.quantity
                            ProductInfo.objects.filter(id=order_item.product_info_id).update(quantity=value)
                    Order.objects.filter(user_id=user.id, state='basket').update(state='Confirmed')

                    superuser=User.objects.get(is_staff=True)
                    orders_list = " ".join(map(str, orders_list))

                    # Отправка заказа администратору для проверки
                    order_user_create_send_mail(superuser.email, superuser.username, user, orders_list)

                    return JsonResponse({'Answer': 'The order has been sent to work!'})
                except:
                    return JsonResponse({'Error': 'Not enough products in stock!'})

            elif serializer.data['state'] == 'Delivered':
                Order.objects.filter(user_id=user.id, state='Delivery').update(state='Delivered')
                return JsonResponse({'Answer': 'Thank you for using the our service!'})

            else:
                return JsonResponse({'Error': 'You can not use this state!'})

        return JsonResponse({'Error': serializer.errors})

# класс для работы администратора

class OrderAdminProcessing(APIView):

    permission_classes = (IsAdminUser,)

    def get(self, request, pk):
        """ Просмотр заказа"""

        try:
            order_dict = {}
            contact_buyer_dict={}

            #загрука данных по покупателю
            order = Order.objects.get(id=pk)
            user_buyer = User.objects.get(id=order.user_id)
            contact = Contact.objects.get(id=order.contact_id)
            orderitem = OrderItem.objects.get(order_id=order.id)
            product = ProductInfo.objects.get(id=orderitem.product_info_id)

            order_dict[order.id] = f'Status: {order.state}, date_create: {order.dt}, model: {product.model},  quantity: {orderitem.quantity}.'
            contact_buyer_dict['-'] = f'Город: {contact.city}, Улица: {contact.street}, Дом: {contact.house}, Корпус: {contact.structure}, ' \
                                             f'Строение: {contact.building}, Квартира: {contact.apartment}, Телефон: {contact.phone}.'

            #загрузка данных по поставщику
            product = ProductInfo.objects.get(external_id=product.external_id)
            shop = Shop.objects.get(id=product.shop_id)
            user_seller = User.objects.get(id=shop.user_id)

            return Response({'Покупатель': {'Фамилия':  user_buyer.last_name, 'Имя':  user_buyer.first_name, 'Адрес доставки': contact_buyer_dict, 'Заказ': order_dict},
                             'Продавец': {'Фамилия':  user_seller.last_name, 'Имя':  user_seller.first_name, 'Магазин': shop.name}})

        except ObjectDoesNotExist:
            return JsonResponse({"Error": "The order not found!"})


    def post(self, request, *args, **kwargs):
        """ Запуск заказа в доставку """

        serializer = OrderProcessingSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # загрузка данных по покупателю
                order = Order.objects.get(id=serializer.data['order'])
                user_buyer = User.objects.get(id=order.user_id)
                contact = Contact.objects.get(id=order.contact_id)
                orderitem = OrderItem.objects.get(order_id=order.id)
                product = ProductInfo.objects.get(id=orderitem.product_info_id)

                order_ = f'{order.id}, Статус: {order.state}, Дата создания заказа: {order.dt}, Модель: {product.model},  Количество: {orderitem.quantity}.'
                contact_buyer_= f'Город: {contact.city}, Улица: {contact.street}, Дом: {contact.house}, Корпус: {contact.structure}, ' \
                           f'Строение: {contact.building}, Квартира: {contact.apartment}, Телефон: {contact.phone}.'

                # загрузка данных по поставщику
                product = ProductInfo.objects.get(external_id=product.external_id)
                shop = Shop.objects.get(id=product.shop_id)
                user_seller = User.objects.get(id=shop.user_id)

                # отправка писем
                order_seller_confirm_send_mail(user_seller.email, user_seller.first_name, user_seller.last_name, order_, contact_buyer_)
                order_buyer_confirm_send_mail(user_buyer.email, user_buyer.first_name, user_buyer.last_name, order_)

                order.state = 'Delivery'
                order.save(update_fields=['state'])

                return JsonResponse({'Answer': 'The order has been sent to delivery!'})

            except:
                return JsonResponse({'Error': 'Order not found!'})

        return JsonResponse({'Error': serializer.errors})

#Классы для работы с фильтром 

class ListProductView(ListAPIView):
    """ по модели и цене"""
    queryset = ProductInfo.objects.all()
    serializer_class = ProductSerializer
    permission_classes = (IsAuthenticated,)

    filter_backends = [SearchFilter,]
    search_fields = ['model', 'price_rrc']
    ordering_filds = ['time_create']


class ListProductDateView(ListAPIView):
    """ по дате"""
    queryset = ProductInfo.objects.all()
    serializer_class = ProductSerializer

    permission_classes = (IsAuthenticated,)
    filterset_class = ProductFilter

class ListCategoryView(ListAPIView):
    """ по категориям"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializers
    permission_classes = (IsAuthenticated,)

    filter_backends = [SearchFilter,]
    search_fields = ['name',]

class ListShopView(ListAPIView):
    """ по Магазину"""
    queryset = Shop.objects.all()
    serializer_class = ShopSerializersFORFilters
    permission_classes = (IsAuthenticated,)

    filter_backends = [SearchFilter,]
    search_fields = ['name',]