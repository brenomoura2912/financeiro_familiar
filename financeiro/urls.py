from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('meus-familiares/', views.meus_familiares_view, name='meus_familiares'),
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('selecionar-familiar/<int:familiar_id>/', views.selecionar_familiar, name='selecionar_familiar'),
    path('categoria/nova/<int:familiar_id>/', views.criar_categoria, name='criar_categoria'),
    path('categoria/<int:categoria_id>/excluir/', views.excluir_categoria, name='excluir_categoria'),
    path('transacao/<int:transacao_id>/editar/', views.editar_transacao, name='editar_transacao'),
    path('transacao/<int:transacao_id>/excluir/', views.excluir_transacao, name='excluir_transacao'),
    path('transacao/exportar/<int:familiar_id>/', views.exportar_csv, name='exportar_csv'),
    path('membros/<int:vinculo_id>/papel/<str:papel>/', views.alterar_papel_membro, name='alterar_papel_membro'),
    path('membros/<int:vinculo_id>/remover/', views.remover_membro, name='remover_membro'),
    path('solicitacao/<int:vinculo_id>/<str:acao>/', views.responder_solicitacao, name='responder_solicitacao'),
]