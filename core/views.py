from django.shortcuts import render,redirect, get_object_or_404
from .models import *
from .forms import *
from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import UserCreationForm
from .forms import RegistrationForm
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets
from .serializers import *
from django.contrib.auth.models import Group
import requests

# Create your views here.
#VIEWSET QUE SE ENCARGA DE INTERCAMBIAR LA DATA
def grupo_requerido(nombre_grupo):
    def decorator(view_fuc):
        @user_passes_test(lambda user: user.groups.filter(name=nombre_grupo).exists())
        def wrapper(request, *arg, **kwargs):
            return view_fuc(request, *arg, **kwargs)
        return wrapper
    return decorator
    
 # @grupo_requerido('cliente')
 # @grupo_requerido('administrador')

class CuponViewset(viewsets.ModelViewSet):
    queryset = Cupon.objects.all()
    serializer_class = CuponSerializer

class ProductoViewset(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class TipoProductoViewset(viewsets.ModelViewSet):
    queryset = TipoProducto.objects.all()
    serializer_class =TipoProductoSerializer

class CarritoViewset(viewsets.ModelViewSet):
    queryset = Carrito.objects.all()
    serializer_class =CarritoSerializer

class UserViewset(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class =UserSerializer





#----------------------------#
def index(request):
    categoria_filtrada = request.GET.get('categoria')  # Obtiene el parámetro de la URL llamado 'categoria'

    if categoria_filtrada:
        url_productos = f'http://127.0.0.1:8000/api/productos/?categoria={categoria_filtrada}'
    else:
        url_productos = 'http://127.0.0.1:8000/api/productos/'

    response_productos = requests.get(url_productos)
    data_productos = response_productos.json()

    data = {
        'listado': data_productos,
        'listado3': data_productos[:4]  # Tomar los primeros 3 elementos de la lista
    }

    return render(request, 'core/index.html', data)

###del api prueba 
def index_api(request):
    #realizamos una solicitud al api| que lo copie el demian por si las dudas que me sale distintos capaz
    response = requests.get('http://127.0.0.1:8000/api/productos/')
    response2 = requests.get('https://mindicador.cl/api')
    response3 = requests.get('https://rickandmortyapi.com/api/character')
   #TRANSFORMA EL JSON PARA LEERLO
    data = response.json()
    moneda = response2.json()
    aux = response3.json()
    personaje = aux['results']

    data = {
        'listado': data,
        'moneda': moneda,
        'pj' :personaje,
        
    }
    

    return render(request, 'core/index-api.html', data)

def base(request):
    carrito = Carrito.objects.filter(usuario=request.user)

    context = {
        'carrito': carrito,
    }
    return render(request, 'core/base.html', context)

def about(request):
    return render(request, 'core/about.html')


def blogSingle(request):
    return render(request, 'core/blog-single.html')


def  blog(request):
    return render(request, 'core/blog.html')

@grupo_requerido('cliente')
def cart(request):
    carrito = Carrito.objects.filter(usuario=request.user)
    codigo_cupon = None
    total_general = 0
    sub_total = 0

    for item in carrito:
        total_producto = item.producto.precio * item.cantidad
        total_general += total_producto
        sub_total += total_producto
        item.total_individual = total_producto

    total_descuento = 0

    # Verificar si el usuario es suscriptor
    try:
        suscriptor = Suscriptor.objects.get(user=request.user)
        if suscriptor.es_suscriptor:
            descuento = suscriptor.descuento / 100
            total_descuento = round(total_general * descuento)
            total_general -= total_descuento
    except Suscriptor.DoesNotExist:
        # Manejar el caso cuando no se encuentra el objeto Suscriptor
        pass

    # Verificar si se ha enviado un cupón en el formulario
    if request.method == 'POST':
        codigo_cupon = request.POST.get('codigo_cupon')
        try:
            cupon = Cupon.objects.get(codigo=codigo_cupon)
            descuento_cupon = round(total_general * (cupon.descuento / 100))
            total_descuento += descuento_cupon
            total_general -= descuento_cupon
        except Cupon.DoesNotExist:
            # Manejar el caso cuando no se encuentra el cupón
            pass

    data = {
        'listado': carrito,
        'final_total': total_general,
        'sub_total': sub_total,
        'descuento': total_descuento,
        'codigo_cupon': codigo_cupon,
        
    }
    return render(request, 'core/cart.html', data)
@grupo_requerido('cliente')
def checkout(request, codigo_cupon=None):
    if request.method == 'POST':
        carrito = Carrito.objects.filter(usuario=request.user)
        
        
        for item in carrito:
            producto = item.producto
            cantidad_comprada = item.cantidad

            # Restar la cantidad comprada del stock del producto
            producto.stock -= cantidad_comprada
            producto.save()
            estado_inicial = 'validacion'
            usuario = request.user
            seguimiento = Seguimiento(usuario=usuario, estado=estado_inicial, producto_id= producto.id)
            seguimiento.save()
            # Crear una instancia de Compra para el historial
            historial = Historial(
                usuario=request.user,
                producto=producto,
                cantidad=cantidad_comprada,
                total=item.producto.precio * cantidad_comprada,
                fecha=datetime.now()
            )
            historial.save()

        # Eliminar los productos del carrito
        carrito.delete()



    carrito = Carrito.objects.filter(usuario=request.user)
    total_general = 0
    sub_total = 0

    for item in carrito:
        item.total = item.producto.precio * item.cantidad
        total_general += item.total
        sub_total += item.total

    # Aplicar descuento si el usuario es suscriptor
    total_descuento = 0
    try:
        suscriptor = get_object_or_404(Suscriptor, user=request.user)
        if suscriptor.es_suscriptor:
            descuento = suscriptor.descuento / 100
            total_descuento = round(total_general * descuento)
            total_general -= total_descuento
    except Suscriptor.DoesNotExist:
        # Manejar el caso cuando no se encuentra el objeto Suscriptor
        pass

    # Aplicar descuento del cupón
    if codigo_cupon:
        cupon = get_object_or_404(Cupon, codigo=codigo_cupon)
        descuento_cupon = round(total_general * (cupon.descuento / 100))
        total_descuento += descuento_cupon
        total_general -= descuento_cupon
    response = requests.get('https://mindicador.cl/api/dolar')
    monedas = response.json()
    valor_dolar = monedas['serie'][0]['valor']#valor del dolar actual
    valor_dolar=round(valor_dolar,2)
    valor=round(total_general/valor_dolar)

    data = {
        'carrito': carrito,
        
        'total_general': total_general,
        'sub_total': sub_total,
        'descuento': total_descuento,
        'codigo_cupon': codigo_cupon,
        'valor': valor
    }


    return render(request, 'core/checkout.html',data)

def contact(request):
    return render(request, 'core/contact.html')

def productSingle(request):
    return render(request, 'core/product-single.html')


def product(request):
    tipos_producto = TipoProducto.objects.all()

    tipo_producto = request.GET.getlist('tipo_producto')  # Obtener los tipos seleccionados

    # Construir la URL de la API
    url_api = 'http://127.0.0.1:8000/api/productos/'
    params = {'tipo_producto': tipo_producto}  # Pasar los tipos seleccionados como parámetros

    # Realizar la solicitud a la API y obtener los datos de productos
    response = requests.get(url_api, params=params)
    data_productos = response.json()

    # Crear listas de productos basadas en los datos de la API
    productos = [Producto(
        id=producto['id'],
        tipo=TipoProducto(id=producto['tipo']['id'], descripcion=producto['tipo']['descripcion']),
        nombre=producto['nombre'],
        precio=producto['precio'],
        stock=producto['stock'],
        descripcion=producto['descripcion'],
        imagen=producto['imagen'],
        created_at=producto['created_at'],
        updated_at=producto['updated_at']
    ) for producto in data_productos]

    # Filtrar productos por tipos seleccionados (opcional)
    if tipo_producto:
        productos = [producto for producto in productos if producto.tipo.descripcion in tipo_producto]

    productoAll = productos[:8]
    producto3 = productos[:3]

    page = request.GET.get('page', 1)

    try:
        paginator = Paginator(productoAll, 6)
        productoAll = paginator.page(page)
    except:
        raise Http404

    data = {
        'tipo': tipos_producto,
        'listado': productoAll,
        'listado3': producto3,
        'tipos_seleccionados': tipo_producto, 
        'paginator': paginator,
    }

    return render(request, 'core/product.html', data)




#creado por sebalol
@grupo_requerido('cliente')
def actualizar(request, id):
    if request.method == 'POST':
        nueva_cantidad = request.POST.get('cantidad')
        item = Carrito.objects.get(id=id)
        item.cantidad = nueva_cantidad
        item.save()
        # Puedes agregar mensajes flash o redirigir a otra página después de la actualización
    return redirect('cart')

@grupo_requerido('cliente')
def agregar(request, id):
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad', 1))
        
        producto = Producto.objects.get(id=id)
        if producto.stock >= cantidad:
            carrito, created = Carrito.objects.get_or_create(producto=producto, usuario=request.user)

            if not created:
                carrito.cantidad += cantidad
            else:
                carrito.cantidad = cantidad
            carrito.save()

            # Mostrar el SweetAlert
            messages.success(request, 'Producto guardado')

    return redirect(request.META.get('HTTP_REFERER') or 'index')

@grupo_requerido('cliente')
def eliminar (request, id):

    carrito = Carrito.objects.get(id=id)
    carrito.delete()
    return redirect('cart')
@grupo_requerido('cliente')
def historial(request):
    compras = Historial.objects.filter(usuario=request.user)
    seguimiento = Seguimiento.objects.filter(usuario=request.user)
    data = {
        'listado': zip(compras, seguimiento)
    }

    return render(request, 'core/wishlist.html', data)
@grupo_requerido('cliente')
def edit(request):
    user = request.user
    suscriptor, created = Suscriptor.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        donation_form = DonationForm(request.POST)

        if user_form.is_valid() and donation_form.is_valid():
            user_form.save()
            donacion = donation_form.cleaned_data['donacion']
            if donacion is not None:
                total_donacion = float(donacion)
                if total_donacion >= 1000:
                    if not suscriptor.es_suscriptor:
                        suscriptor.es_suscriptor = True
                        suscriptor.descuento = 5
                        suscriptor.save()
                else:
                    donation_form.add_error('donacion', 'La donación debe ser de al menos 1000')

            cancelar_suscripcion = request.POST.get('cancelar_suscripcion')
            if cancelar_suscripcion:
                cancelar_suscripcion(request, suscriptor)

    else:
        user_form = UserEditForm(instance=user)
        donation_form = DonationForm()

    response = requests.get('https://mindicador.cl/api/dolar')
    monedas = response.json()
    valor_dolar = monedas['serie'][0]['valor']  # Valor del dólar actual
    valor_dolar = round(valor_dolar, 2)

    if 'total_donacion' in locals():
        valor = round(total_donacion / valor_dolar, 2)
    else:
        valor = None

    context = {
        'user_form': user_form,
        'donation_form': donation_form,
        'suscriptor': suscriptor,
        'donacion': valor,
    }

    return render(request, 'core/edit.html', context)
def edit(request):
    user = request.user
    suscriptor, created = Suscriptor.objects.get_or_create(user=user)

    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        donation_form = DonationForm(request.POST)

        if user_form.is_valid() and donation_form.is_valid():
            user_form.save()
            donacion = donation_form.cleaned_data['donacion']
            if donacion is not None:
                total_donacion = float(donacion)
                if total_donacion >= 1000:
                    if not suscriptor.es_suscriptor:
                        suscriptor.es_suscriptor = True
                        suscriptor.descuento = 5
                        suscriptor.save()
                else:
                    donation_form.add_error('donacion', 'La donación debe ser de al menos 1000')

            cancelar_suscripcion = request.POST.get('cancelar_suscripcion')
            if cancelar_suscripcion:
                cancelar_suscripcion(request, suscriptor)

    else:
        user_form = UserEditForm(instance=user)
        donation_form = DonationForm()

    response = requests.get('https://mindicador.cl/api/dolar')
    monedas = response.json()
    valor_dolar = monedas['serie'][0]['valor']  # Valor del dólar actual
    valor_dolar = round(valor_dolar, 2)

    if 'total_donacion' in locals():
        valor = round(total_donacion / valor_dolar, 2)
    else:
        valor = None

    context = {
        'user_form': user_form,
        'donation_form': donation_form,
        'suscriptor': suscriptor,
        'donacion': valor,
    }

    return render(request, 'core/edit.html', context)


@grupo_requerido('cliente')
def eliminar_perfil(request):
    user = request.user
    user.delete()
    # Realiza cualquier otra acción necesaria después de eliminar el perfil
    return redirect('index') 
@grupo_requerido('cliente')
def cancelar_suscripcion(request):
    user = request.user
    suscriptor = Suscriptor.objects.get(user=user)
    suscriptor.es_suscriptor = False
    suscriptor.descuento = 0
    suscriptor.save()
    
    return redirect('edit') 
#CREADO POR REIKOM:

def product_details(request, id):
    producto = Producto.objects.get(id=id)
    objeto_aleatorio = Producto.objects.all().order_by('?')
    data = {
        'producto': producto,
        'random':objeto_aleatorio
    }
    
    
    return render(request, 'core/product-single.html', data)

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            grupo = Group.objects.get(name='cliente')
            user.groups.add(grupo) # Guardar el usuario registrado
            suscriptor = Suscriptor(user=user)  # Crear un objeto Suscriptor con el usuario
            suscriptor.save()  # Guardar el objeto Suscriptor en la base de datos
            return redirect('login')  # Redirige al inicio de sesión después del registro exitoso
    else:
        form = RegistrationForm()
    return render(request, 'registration/register.html', {'form': form})
@grupo_requerido('administrador')
def add(request):
    page = request.GET.get('page', 1)
    data = {
        'form': ProductoForm()
    }

    if request.method == 'POST':
        formulario = ProductoForm(request.POST, files=request.FILES)
        if formulario.is_valid ():
            formulario.save()
            #data['msj'] = "Producto guardado correctamente" 
            messages.success(request, "Producto almacenado correctamente")  
    return render(request, 'core/add-product.html',data)
@grupo_requerido('administrador')
def delate(request, id):
    producto = Producto.objects.get(id=id)
    producto.delete()
    return redirect(to = 'index')

@grupo_requerido('administrador')
def update(request, id):
    producto = Producto.objects.get(id=id)
    data = {
        'form': ProductoForm(instance =producto)
    }

    if request.method == 'POST':
        formulario = ProductoForm(data = request.POST, files=request.FILES,instance=producto)
        if formulario.is_valid():
            formulario.save()
            #data['msj'] = "Producto modificado correctamente"
            messages.success(request, "Producto modificado correctamente") 
            data['form'] = formulario
    
    return render(request, 'core/update-product.html', data)

#CERRAR CREADOS POR REIKOM


#CREADO POR EL CRACK
@grupo_requerido('administrador')
def crear_cupon(request):
    if request.method == 'POST':
        form = CuponForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_cupones')
    else:
        form = CuponForm()
    
    return render(request, 'core/crear_cupon.html', {'form': form})
@grupo_requerido('administrador')
def lista_cupones(request):
    cupones = Cupon.objects.all()
    return render(request, 'core/lista_cupones.html', {'cupones': cupones})
@grupo_requerido('administrador')
def actualizar_cupon(request, id):
    cupon = get_object_or_404(Cupon, id=id)
    
    if request.method == 'POST':
        form = CuponForm(request.POST, instance=cupon)
        if form.is_valid():
            form.save()
            return redirect('lista_cupones')
    else:
        form = CuponForm(instance=cupon)
    
    return render(request, 'core/actualizar_cupon.html', {'form': form})

@grupo_requerido('administrador')
def eliminar_cupon(request, id):
    cupon = get_object_or_404(Cupon, id=id)
    cupon.delete()
    return redirect('lista_cupones')
@grupo_requerido('administrador')
def cambiar_estado_seguimiento(request):
    seguimientos = Seguimiento.objects.all()

    if request.method == 'POST':
        for seguimiento in seguimientos:
            nuevo_estado = request.POST.get(f'nuevo_estado_{seguimiento.id}')
            seguimiento.estado = nuevo_estado
            seguimiento.save()
        return redirect('historial')

    return render(request, 'core/cambiar_estado_seguimiento.html', {'seguimientos': seguimientos})

