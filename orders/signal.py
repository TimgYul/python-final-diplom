from django.core.mail import send_mail

def create_user_send_mail(email, first_name, last_name, token):
    subject = "Сообщение от  Сервиса заказа товаров для розничных сетей "
    message = f"Уважаемый {first_name} {last_name},\nВы получили это письмо т.к. создали нового пользователя в нашем сервисе.\nДля дальнейшего взаимодействия с нашим сервисом используйте" \
              f" токен:\n{token}"
    send_mail(subject, message, from_email=None, recipient_list=[email])

def update_user_send_mail(email, first_name, last_name, token):
    subject = "Сообщение от  Сервиса заказа товаров для розничных сетей "
    message = f"Уважаемый {first_name} {last_name},\nВы получили это письмо т.к. изменили учетные данные пользователя в нашем сервисе." \
              f"\nДля дальнейшего взаимодействия с нашим сервисом используйте новый " \
              f" токен:\n{token}"
    send_mail(subject, message, from_email=None, recipient_list=[email])

def order_user_create_send_mail(email, username, user, orders_list):
    subject = "Сообщение от  Сервиса заказа товаров для розничных сетей "
    message = f"Уважаемый {username}.\nВы получили это письмо т.к. пользователь {user.last_name} {user.first_name} подтвердил заказ." \
              f"\nНомера заказов: {orders_list}." \
              f"\nПроверьте координаты доставки. После передайте заказ в доставку."

    send_mail(subject, message, from_email=None, recipient_list=[email])

def order_seller_confirm_send_mail(email, first_name, last_name, order_dict, contact_buyer_dict):
    subject = "Сообщение от  Сервиса заказа товаров для розничных сетей "
    message = f"Уважаемый {first_name} {last_name},\nВы получили это письмо т.к. покупатель создал заказ." \
              f"\nЗаказ: {order_dict}." \
              f"\nАдрес доставки заказа: {contact_buyer_dict}."

    send_mail(subject, message, from_email=None, recipient_list=[email])

def order_buyer_confirm_send_mail(email, first_name, last_name, order_dict):
    subject = "Сообщение от  Сервиса заказа товаров для розничных сетей "
    message = f"Уважаемый {first_name} {last_name},\nВы получили это письмо т.к. ваш заказ" \
              f"\nЗаказ: {order_dict}." \
              f"\nБыл передан в доставку. После доставки переведите статус заказа в Доставлено (Delivered)."

    send_mail(subject, message, from_email=None, recipient_list=[email])