from django.contrib import admin
from .models import (
    PerfilUsuario,
    Familiar,
    VinculoFamiliar,
    Categoria,
    Transacao,
    FechamentoMes,
    LogAuditoria,
    CodigoVerificacaoEmail,
)

admin.site.register(PerfilUsuario)
admin.site.register(Familiar)
admin.site.register(VinculoFamiliar)
admin.site.register(Categoria)
admin.site.register(Transacao)
admin.site.register(FechamentoMes)
admin.site.register(LogAuditoria)
admin.site.register(CodigoVerificacaoEmail)