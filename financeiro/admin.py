from django.contrib import admin
from .models import Familiar, VinculoFamiliar, Categoria, Transacao

@admin.register(Familiar)
class FamiliarAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_convite', 'data_nascimento', 'criado_em')
    search_fields = ('nome', 'codigo_convite')

@admin.register(VinculoFamiliar)
class VinculoFamiliarAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'familiar', 'papel', 'status', 'solicitado_em')
    list_filter = ('papel', 'status')
    search_fields = ('usuario__username', 'familiar__nome')

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'familiar')
    list_filter = ('tipo', 'familiar')
    search_fields = ('nome',)

@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('data', 'familiar', 'descricao', 'valor', 'tipo', 'comprador', 'forma_pagamento')
    list_filter = ('tipo', 'forma_pagamento', 'familiar', 'data')
    search_fields = ('descricao', 'comprador', 'familiar__nome')
    date_hierarchy = 'data'