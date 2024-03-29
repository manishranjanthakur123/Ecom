from django.shortcuts import render, redirect, get_object_or_404
from .models import Order, OrderItem
from .form import OrderCreateForm
from cart.cart import Cart
from .tasks import order_created
from django.urls import reverse

from django.contrib.admin.views.decorators import staff_member_required

from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string
import weasyprint


# Create your views here.
def order_create(request):
    cart = Cart(request)
    if request.method =='POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart.cart:
                OrderItem.objects.create(order=order, product=cart.cart[item]['product'], price=cart.cart[item]['price'], quantity=cart.cart[item]['quantity'])
            cart.clear()   # clear cart after order is persisted
            # launch asynchronous task
            order_created.delay(order.id)
            # set the order in the session
            request.session['order_id'] = order.id
            # redirect for payment
            return redirect(reverse('payment:process'))
    else:
        form = OrderCreateForm(request.POST)
        return render(request, 'orders/order/create.html', {'form': form, 'cart':cart})


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/order/detail.html', {'order': order})


@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/order/pdf.html', {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'filename=\ "order_{}.pdf"'.format(order.id)
    weasyprint.HTML(string=html).write_pdf(response, stylesheets=[weasyprint.CSS(settings.STATIC_ROOT + 'css/pdf.css')])
    return response