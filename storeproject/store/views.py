
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q
from django.shortcuts import (
    render, redirect, get_object_or_404
)

from .models import (
    Product, Category, Banner,
    CartItem, Order, OrderItem
)


def home(request):
    products = Product.objects.filter(is_active=True)
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )

    if category_id.isdigit():
        products = products.filter(category_id=int(category_id))

    context = {
        'banners': Banner.objects.filter(is_active=True),
        'categories': Category.objects.all(),
        'products': products,
        'featured_products': Product.objects.filter(
            is_active=True, is_featured=True
        ),
        'query': query,
        'selected_category': category_id,
    }
    return render(request, 'home.html', context)


def product_detail(request, id):
    product = get_object_or_404(
        Product, id=id, is_active=True
    )
    return render(
        request,
        'product_detail.html',
        {'product': product}
    )


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully.')
            return redirect('account')
    else:
        form = UserCreationForm()
        
    form.fields['username'].help_text = ''
    form.fields['password1'].help_text = ''
    form.fields['password2'].help_text = ''    

    return render(request, 'register.html', {'form': form})


@login_required
def account(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'account.html', {
        'orders': orders,
    })


@login_required
def add_to_cart(request, id):
    if request.method != 'POST':
        return redirect('home')

    product = get_object_or_404(
        Product, id=id, is_active=True
    )

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        messages.error(request, 'Invalid quantity.')
        return redirect('product_detail', id=id)

    if quantity < 1:
        messages.error(request, 'Quantity must be at least 1.')
        return redirect('product_detail', id=id)

    item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product,
        defaults={'quantity': quantity}
    )

    if not created:
        item.quantity += quantity

    if item.quantity > product.stock:
        if created:
            item.delete()
        messages.error(
            request, 'Requested quantity exceeds available stock.'
        )
        return redirect('product_detail', id=id)

    item.save()
    messages.success(request, 'Product added to your cart.')
    return redirect('cart')


@login_required
def cart(request):
    items = CartItem.objects.filter(
        user=request.user,
        product__is_active=True
    ).select_related('product')

    total = sum(
        (item.subtotal for item in items),
        Decimal('0.00')
    )

    return render(request, 'cart.html', {
        'items': items,
        'total': total,
    })


@login_required
def update_cart(request, id):
    if request.method != 'POST':
        return redirect('cart')

    item = get_object_or_404(
        CartItem, id=id, user=request.user
    )

    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        messages.error(request, 'Invalid quantity.')
        return redirect('cart')

    if quantity < 1:
        messages.error(request, 'Quantity must be at least 1.')
    elif not item.product.is_active:
        messages.error(request, 'This product is unavailable.')
    elif quantity > item.product.stock:
        messages.error(request, 'Not enough stock available.')
    else:
        item.quantity = quantity
        item.save(update_fields=['quantity'])
        messages.success(request, 'Cart updated.')

    return redirect('cart')


@login_required
def remove_from_cart(request, id):
    if request.method != 'POST':
        return redirect('cart')

    item = get_object_or_404(
        CartItem, id=id, user=request.user
    )
    item.delete()
    messages.success(request, 'Item removed from cart.')
    return redirect('cart')


@login_required
def checkout(request):
    if request.method != 'POST':
        items = CartItem.objects.filter(
            user=request.user,
            product__is_active=True
        ).select_related('product')

        if not items.exists():
            messages.info(request, 'Your cart is empty.')
            return redirect('cart')

        total = sum(
            (item.subtotal for item in items),
            Decimal('0.00')
        )

        return render(request, 'checkout.html', {
            'items': items,
            'total': total,
        })

    full_name = request.POST.get('full_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    city = request.POST.get('city', '').strip()
    postal_code = request.POST.get('postal_code', '').strip()

    if not all([full_name, phone, address, city, postal_code]):
        messages.error(request, 'Please complete all delivery fields.')
        return redirect('checkout')

    if len(phone) > 20 or len(postal_code) > 12:
        messages.error(request, 'Phone or postal code is too long.')
        return redirect('checkout')

    try:
        with transaction.atomic():
            items = list(
                CartItem.objects.filter(
                    user=request.user
                ).select_related('product')
            )

            if not items:
                messages.error(request, 'Your cart is empty.')
                return redirect('cart')

            total = Decimal('0.00')
            order_lines = []

            for item in items:
                product = Product.objects.select_for_update().get(
                    pk=item.product_id
                )

                if not product.is_active:
                    raise ValueError(
                        f'{product.name} is no longer available.'
                    )

                if item.quantity > product.stock:
                    raise ValueError(
                        f'Insufficient stock for {product.name}.'
                    )

                total += product.price * item.quantity
                order_lines.append(
                    (product, item.quantity, product.price)
                )

            order = Order.objects.create(
                user=request.user,
                full_name=full_name,
                phone=phone,
                address=address,
                city=city,
                postal_code=postal_code,
                total_amount=total,
            )

            for product, quantity, price in order_lines:
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=price,
                    quantity=quantity,
                )
                product.stock -= quantity
                product.save(update_fields=['stock'])

            CartItem.objects.filter(user=request.user).delete()

    except ValueError as error:
        messages.error(request, str(error))
        return redirect('cart')

    return redirect('order_success', id=order.id)


@login_required
def order_success(request, id):
    order = get_object_or_404(
        Order, id=id, user=request.user
    )
    return render(
        request, 'order_success.html', {'order': order}
    )


@login_required
def order_history(request):
    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'orders.html', {
        'orders': orders,
    })


@login_required
def order_detail(request, id):
    order = get_object_or_404(
        Order, id=id, user=request.user
    )
    return render(request, 'order_detail.html', {
        'order': order,
    })
