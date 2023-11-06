from rest_framework import serializers
from django.contrib.auth.models import User
from orders.models import Shop, Category, Contact, Product, ProductInfo, ProductParameter, OrderItem, Order
from rest_framework.authtoken.models import Token
from orders.signal import create_user_send_mail, update_user_send_mail
import yaml
from yaml.loader import Loader
import requests
from orders.permissions import get_username


class ShopUserSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения пользователя"""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']


class UserSerializer(serializers.ModelSerializer):
    """Класс создает, обновляет пользователя и отправляет письма о успешном создании, обновлении"""
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'password']


    def create(self, validated_data):
        user = super().create(validated_data)
        token = Token.objects.create(user=user)

        create_user_send_mail(user.email, user.first_name, user.last_name, token) # Отправляем письмо о создании пользователя

        return user

    def update(self, instance, validated_data):

        user = super().update(instance, validated_data)

        token_old = Token.objects.get(user=user)
        token_old.delete()

        token_new = Token.objects.create(user=user)
        update_user_send_mail(user.email, user.first_name, user.last_name, token_new) # Отправляем письмо о изменении пользователя

        return user


class ContactSerializer(serializers.ModelSerializer):
    """Класс создает контакт"""
    class Meta:
        model = Contact
        fields = ['id', 'city', 'street', 'house', 'structure', 'building', 'apartment',  'phone', 'user']

    def create(self, validated_data):
        city = validated_data.get('city')
        street = validated_data.get('street')
        house = validated_data.get('house')
        structure = validated_data.get('structure')
        building = validated_data.get('building')
        apartment = validated_data.get('apartment')
        phone = validated_data.get('phone')

        request = self.context['request']
        user_id = get_username(request)

        contact = Contact.objects.create(user_id=user_id, city=city, street=street, house=house, structure=structure,
                                         building=building, apartment=apartment, phone=phone )

        return contact

class ShopSerializerForDisplayUser(serializers.ModelSerializer):
    """Сериализатор для отображения данных пользователя при просмотре списка магазинов"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name',]

class ShopSerializer(serializers.ModelSerializer):
    """Класс создает магазин, категории товаров и делает связь между ними, производит наполнение из прайса"""

    class Meta:
        model = Shop
        fields = ['id', 'name', 'url', 'state', 'user', ]

    user = ShopSerializerForDisplayUser(read_only=True)

    def create(self, validated_data):
        name = validated_data.get('name')
        url = validated_data.get('url')
        state = True # Указываем, что магазин активен

        request = self.context['request']
        user_id = get_username(request)

        stream = requests.get(url).content
        price_list = yaml.load(stream, Loader=Loader) # Загрузка прайса

        shop = Shop.objects.create(name=name, url=url, user_id=user_id, state=state)

        for category in price_list['categories']:
            cat = Category.objects.create(id=category['id'], name=category['name'])
            shop.categories.add(cat)

        for element in price_list['goods']:
            product = Product.objects.create(name=element['name'],
                                             category_id=element['category'])
            product_info = ProductInfo.objects.create(product_id=product.id,
                                                      external_id=element['id'],
                                                      model=element['model'],
                                                      price=element['price'],
                                                      price_rrc=element['price_rrc'],
                                                      quantity=element['quantity'],
                                                      shop_id=shop.id)
            for key, value in element['parameters'].items():
                ProductParameter.objects.create(product_info_id=product_info.id,
                                                name=key,
                                                value=value)
        return shop


class ParametrsSerializerFORProduct(serializers.ModelSerializer):
    """Сериализатор для отображения информации по техническим характеристикам товара (Используется для фильтрации по продуктам)"""
    class Meta:
        model = ProductParameter
        fields = ['name', 'value']


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения информации по продуктам"""
    class Meta:
        model = ProductInfo
        fields = ['model', 'external_id', 'quantity', 'price_rrc', 'product_parameters', ]

    product_parameters = ParametrsSerializerFORProduct(many=True)


class ParametrsSerializerFORCategory(serializers.ModelSerializer):
    """Сериализатор для отображения информации по продуктам (Используется для фильтрации по категориям)"""
    class Meta:
        model = ProductParameter
        fields = ['name','product_infos']

    product_infos = ProductSerializer(many=True)


class CategorySerializers(serializers.ModelSerializer):
    """Сериализатор для отображения информации по категориям """
    class Meta:
        model = Category
        fields = ['name', 'products']

    products =ParametrsSerializerFORCategory(many=True)


class ShopSerializersFORFilters(serializers.ModelSerializer):
    """Сериализатор для отображения информации по магазинам"""
    class Meta:
        model = Shop
        fields = ['name', 'product_infos']

    product_infos = ProductSerializer(many=True)


class OrderSerializer(serializers.Serializer):
    """Сериализатор для создания заказа"""
    shop = serializers.CharField(max_length=50)
    external_id = serializers.IntegerField()
    quantity = serializers.IntegerField()


class OrderProcessingSerializer(serializers.Serializer):
    """Сериализатор для обработки заказа"""
    state = serializers.CharField(max_length=50, required=False)
    order = serializers.IntegerField(required=False)