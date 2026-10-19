from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('cadastro/', views.cadastro_view, name='cadastro'),
    path('logout/', views.logout_view, name='logout'),
    path('onboarding/', views.onboarding_view, name='onboarding'),
    path('meus-familiares/', views.meus_familiares_view, name='meus_familiares'),
    path('selecionar-familiar/<int:familiar_id>/', views.selecionar_familiar, name='selecionar_familiar'),
    path('', views.index, name='index'),

    # Perfil do Utilizador
    path('perfil/', views.perfil_view, name='perfil'),
    path('perfil/remover-foto/', views.remover_foto_perfil, name='remover_foto_perfil'),

    # Gestão de Transações
    path('transacao/<int:transacao_id>/editar/', views.editar_transacao, name='editar_transacao'),
    path('transacao/<int:transacao_id>/excluir/', views.excluir_transacao, name='excluir_transacao'),
    path('exportar-csv/<int:familiar_id>/', views.exportar_csv, name='exportar_csv'),

    # Governança e Categorias
    path('familiar/<int:familiar_id>/fechamento/<int:ano>/<int:mes>/', views.alternar_fechamento_mes, name='alternar_fechamento_mes'),
    path('familiar/<int:familiar_id>/arquivar/', views.alternar_arquivamento_familiar, name='alternar_arquivamento_familiar'),
    path('familiar/<int:familiar_id>/excluir-definitivo/', views.excluir_familiar_definitivo, name='excluir_familiar_definitivo'),
    path('familiar/<int:familiar_id>/sair/', views.sair_da_familia, name='sair_da_familia'),
    path('familiar/<int:familiar_id>/categoria/criar/', views.criar_categoria, name='criar_categoria'),
    path('categoria/<int:categoria_id>/excluir/', views.excluir_categoria, name='excluir_categoria'),

    # Membros e Convites
    path('solicitacao/<int:vinculo_id>/<str:acao>/', views.responder_solicitacao, name='responder_solicitacao'),
    path('membro/<int:vinculo_id>/papel/<str:papel>/', views.alterar_papel_membro, name='alterar_papel_membro'),
    path('membro/<int:vinculo_id>/remover/', views.remover_membro, name='remover_membro'),
]