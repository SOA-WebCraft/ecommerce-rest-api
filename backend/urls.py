from contextvars import Token
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.conf import settings
from fullstack  import views, auth, login_view, logout_view




urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('fullstack.urls')),
    path('api/users/register/', views.RegisterUser.as_view(), name='register' ),
    path('api/users/login/', login_view.CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', login_view.CookieTokenRefreshView.as_view(), name='token_refresh'),
    path('api/users/logout/', logout_view.LogoutView.as_view(), name='logout'),
    path('api/test/', views.Testauthentication.as_view(), name='test'),
    path('api/csrf/', views.CsrfView.as_view(), name='csrf'),
     
    
    
]

if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)