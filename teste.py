import sys

sys.stdout.reconfigure(encoding="utf-8")

from resumo_operacional import (
    gerar_resumo_diario,
    gerar_resumo_semanal
)

print("\n" + "=" * 50)
print("RESUMO DIÁRIO")
print("=" * 50)
print(gerar_resumo_diario())

print("\n" + "=" * 50)
print("RESUMO SEMANAL")
print("=" * 50)
print(gerar_resumo_semanal())