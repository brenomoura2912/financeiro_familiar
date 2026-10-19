from django.contrib import admin
from .models import (
    Familiar,
    VinculoFamiliar,
    Categoria,
    Transacao,
    FechamentoCompetencia,
    LogAuditoriaTransacao,
)


@admin.register(Familiar)
class FamiliarAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_convite', 'ativo', 'criado_em')
    search_fields = ('nome', 'codigo_convite')
    list_filter = ('ativo',)


@admin.register(VinculoFamiliar)
class VinculoFamiliarAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'familiar', 'papel', 'status', 'criado_em')
    list_filter = ('papel', 'status', 'familiar')
    search_fields = ('usuario__username', 'usuario__email', 'familiar__nome')


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'familiar', 'tipo')
    list_filter = ('tipo', 'familiar')
    search_fields = ('nome', 'familiar__nome')


@admin.register(Transacao)
class TransacaoAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'familiar', 'tipo', 'valor', 'data', 'comprador', 'forma_pagamento')
    list_filter = ('tipo', 'forma_pagamento', 'familiar', 'data')
    search_fields = ('descricao', 'comprador', 'observacoes')


@admin.register(FechamentoCompetencia)
class FechamentoCompetenciaAdmin(admin.ModelAdmin):
    list_display = ('familiar', 'mes', 'ano', 'fechado', 'fechado_por', 'fechado_em')
    list_filter = ('fechado', 'ano', 'mes', 'familiar')


@admin.register(LogAuditoriaTransacao)
class LogAuditoriaTransacaoAdmin(admin.ModelAdmin):
    list_display = ('familiar', 'acao', 'transacao_id_ref', 'usuario', 'data_hora')
    list_filter = ('acao', 'familiar', 'data_hora')
    search_fields = ('detalhes', 'usuario__username')