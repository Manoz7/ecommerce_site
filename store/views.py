import django
from django.contrib.auth.models import User
from store.models import Address, Cart, Category, Order, Product
from django.shortcuts import redirect, render, get_object_or_404
from .forms import RegistrationForm, AddressForm
from django.contrib import messages
from django.views import View
import decimal
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator # for Class Based Views
from django.utils import timezone
from xhtml2pdf import pisa

# Create your views here.

def home(request):
    categories = Category.objects.filter(is_active=True, is_featured=True)[:3]
    products = Product.objects.filter(is_active=True, is_featured=True)[:8]
    context = {
        'categories': categories,
        'products': products,
    }
    return render(request, 'store/index.html', context)


def detail(request, slug):
    product = get_object_or_404(Product, slug=slug)
    related_products = Product.objects.exclude(id=product.id).filter(is_active=True, category=product.category)
    context = {
        'product': product,
        'related_products': related_products,

    }
    return render(request, 'store/detail.html', context)


def all_categories(request):
    categories = Category.objects.filter(is_active=True)
    return render(request, 'store/categories.html', {'categories':categories})


def category_products(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(is_active=True, category=category)
    categories = Category.objects.filter(is_active=True)
    context = {
        'category': category,
        'products': products,
        'categories': categories,
    }
    return render(request, 'store/category_products.html', context)


# Authentication Starts Here

class RegistrationView(View):
    def get(self, request):
        form = RegistrationForm()
        return render(request, 'account/register.html', {'form': form})
    
    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            messages.success(request, "Congratulations! Registration Successful!")
            form.save()
        return render(request, 'account/register.html', {'form': form})
        

@login_required
def profile(request):
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user)
    return render(request, 'account/profile.html', {'addresses':addresses, 'orders':orders})


@method_decorator(login_required, name='dispatch')
class AddressView(View):
    def get(self, request):
        form = AddressForm()
        return render(request, 'account/add_address.html', {'form': form})

    def post(self, request):
        form = AddressForm(request.POST)
        if form.is_valid():
            user=request.user
            locality = form.cleaned_data['locality']
            city = form.cleaned_data['city']
            state = form.cleaned_data['state']
            reg = Address(user=user, locality=locality, city=city, state=state)
            reg.save()
            messages.success(request, "New Address Added Successfully.")
        return redirect('store:profile')


@login_required
def remove_address(request, id):
    address = get_object_or_404(Address, user=request.user, id=id)
    if request.method == 'POST':
        address.delete()
        messages.success(request, "Address removed.")
        return redirect('store:profile')
    return render(request, 'store/remove_address.html', {'address': address})

@login_required
def add_to_cart(request):
    user = request.user
    product_id = request.GET.get('prod_id')
    product = get_object_or_404(Product, id=product_id)

    # Check whether the Product is alread in Cart or Not
    item_already_in_cart = Cart.objects.filter(product=product_id, user=user)
    if item_already_in_cart:
        cp = get_object_or_404(Cart, product=product_id, user=user)
        cp.quantity += 1
        cp.save()
    else:
        Cart(user=user, product=product).save()
    
    return redirect('store:cart')


@login_required
def cart(request):
    user = request.user
    cart_products = Cart.objects.filter(user=user)

    # Display Total on Cart Page
    amount = decimal.Decimal(0)
    shipping_amount = decimal.Decimal(10)
    # using list comprehension to calculate total amount based on quantity and shipping
    cp = [p for p in Cart.objects.all() if p.user==user]
    if cp:
        for p in cp:
            temp_amount = (p.quantity * p.product.price)
            amount += temp_amount

    # Customer Addresses
    addresses = Address.objects.filter(user=user)

    context = {
        'cart_products': cart_products,
        'amount': amount,
        'shipping_amount': shipping_amount,
        'total_amount': amount + shipping_amount,
        'addresses': addresses,
    }
    return render(request, 'store/cart.html', context)


@login_required
def remove_cart(request, cart_id):
    if request.method == 'GET':
        c = get_object_or_404(Cart, id=cart_id)
        c.delete()
        messages.success(request, "Product removed from Cart.")
    return redirect('store:cart')


@login_required
def plus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        cp.quantity += 1
        cp.save()
    return redirect('store:cart')


@login_required
def minus_cart(request, cart_id):
    if request.method == 'GET':
        cp = get_object_or_404(Cart, id=cart_id)
        # Remove the Product if the quantity is already 1
        if cp.quantity == 1:
            cp.delete()
        else:
            cp.quantity -= 1
            cp.save()
    return redirect('store:cart')

# @login_required
# def checkout(request):
#     user = request.user
#     addresses = Address.objects.filter(user=user)
#     cart_products = Cart.objects.filter(user=user)

#     if request.method == 'POST':
#         form = AddressForm(request.POST)
#         if form.is_valid():
#             address = form.save(commit=False)
#             address.user = user
#             address.save()

#             if cart_products:
#                 for cart_product in cart_products:
#                     # Create an order for each cart product
#                     Order.objects.create(
#                         user=user,
#                         address=address,
#                         product=cart_product.product,
#                         quantity=cart_product.quantity
#                     )

#                 # Clear the user's cart after creating orders
#                 cart_products.delete()

#                 messages.success(request, "Order placed successfully. Thank you!")
#                 return redirect('store:orders')

#     else:
#         form = AddressForm()

#     total_amount = sum(cart_product.total_price for cart_product in cart_products)
#     shipping_amount = decimal.Decimal(10)  # Assuming shipping cost is $10

#     context = {
#         'addresses': addresses,
#         'form': form,
#         'cart_products': cart_products,
#         'total_amount': total_amount,
#         'shipping_amount': shipping_amount,
#         'total_with_shipping': total_amount + shipping_amount,
#     }
#     return render(request, 'store/checkout.html', context)


@login_required
def checkout(request):
    user = request.user
    addresses = Address.objects.filter(user=user)
    cart_products = Cart.objects.filter(user=user)

    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = user
            address.save()

            if cart_products:
                total_amount = sum(cart_product.total_price for cart_product in cart_products)
                shipping_amount = decimal.Decimal(10)  # Assuming shipping cost is $10

                # Create the order for each cart product
                for cart_product in cart_products:
                    Order.objects.create(
                        user=user,
                        address=address,
                        product=cart_product.product,
                        quantity=cart_product.quantity,
                        ordered_date=timezone.now(),
                        status="Pending"  # You can set the initial status as "Pending"
                    )
                    # Update the stock quantity of the product
                    cart_product.product.update_stock(cart_product.quantity)

                # Clear the user's cart after creating orders
                cart_products.delete()

                # Generate and serve the invoice as a PDF (similar to the previous code)
                # ...

                messages.success(request, "Order placed successfully. Thank you!")
                return redirect('store:orders')
    
    

    else:
        form = AddressForm()

    total_amount = sum(cart_product.total_price for cart_product in cart_products)
    shipping_amount = decimal.Decimal(10)  # Assuming shipping cost is $10

    context = {
        'addresses': addresses,
        'form': form,
        'cart_products': cart_products,
        'total_amount': total_amount,
        'shipping_amount': shipping_amount,
        'total_with_shipping': total_amount + shipping_amount,
    }
    return render(request, 'store/checkout.html', context)


@login_required
def orders(request):
    all_orders = Order.objects.filter(user=request.user).order_by('-ordered_date')
    return render(request, 'store/orders.html', {'orders': all_orders})





def shop(request):
    return render(request, 'store/shop.html')





def test(request):
    return render(request, 'store/test.html')
