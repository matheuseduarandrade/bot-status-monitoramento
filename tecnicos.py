"""
tecnicos.py

Lista oficial de técnicos em campo.
Usada para normalizar nomes parciais/apelidos nas buscas do bot.
"""

# Lista completa de técnicos (nome exato como aparece no Jira)
TECNICOS = [
    "ADRIANO LUIS VIVAN",
    "Abner Bautista Alvarez Santos",
    "Adriano Luis Vivan",
    "Adriel Carlos Da Costa Ferreira",
    "Alexvan Santos de Oliveira",
    "Alisson Pavão Agostinho",
    "Anderson Fernandes de Amorim",
    "André Cristian Januário Santos",
    "André Luiz Marques",
    "André dos Reis Marques",
    "Angelo Marcos Rafael",
    "Bernardo Santos da Cunha",
    "Breno Arruda Vilaca",
    "Bruno Felipe dos Santos Silva",
    "Bruno Sousa dos Santos",
    "CLAUBER RIBEIRO CANHETE",
    "CLAUDINEIS APARECIDO DOS SANTOS",
    "Cairan Andre Morais Texeira",
    "Carlos William Leite de Medeiros",
    "Diego Muniz Silva",
    "Douglas Venancio Ferreira",
    "Edgar Gomes Pereira",
    "Eduardo Correa do Prado",
    "Eduardo Mascarenhas",
    "Emerson Modesto de Sousa",
    "Fagner de Lanes Fernando",
    "Felipe da Silva Trindade",
    "Fernando Machado Dornelles",
    "Fernando Prado de Oliveira",
    "Flavio Rocha Bastos",
    "Francisco Eujanio Nascimento Barros",
    "Francisco Renan Marques da Silva",
    "GABRIEL LUCAS CAETANO DA SILVA",
    "GABRIEL LUCAS CAETANO SILVA",
    "Hugo Cesar dos Santos",
    "Hugo Cesar dos santos",
    "Irving Simões Pereira",
    "Ivan dos Santos Oliveira",
    "Jalcimar Mota de Sousa",
    "Jeferson Dutra Amarante",
    "Joarez Soares de Oliveira Junior",
    "Jose Amilton Procenia Alves",
    "Jose Romário Coelho de Souza",
    "José Carlos da Silva Ricardo",
    "José Marcos Gomes de Sousa",
    "João Lucas Martins da Silva",
    "João Reis dos Santos Costa Filho",
    "Juliano Gilberto Martins",
    "Kenidy Jussiane do Amaral",
    "Klebeson Modesto Sousa",
    "LEANDRO CARVALHO DA COSTA",
    "Lauro Ripeto Ribeiro",
    "Luan Amaro dos Santos Pereira",
    "Lucas Roese Bernardo",
    "Luis Fernando Rodrigues Alves",
    "Luiz Fernando Tomaz da Silva",
    "Luiz Ricardo Monteiro da Silva",
    "MAGNO NASCIMENTO DE ARAUJO",
    "MARIO MATTE",
    "Marcos José de Oliveira",
    "Marcos Lean Magalhaes Lima",
    "Mauro Cezar Silva da Silva",
    "Michael Gledson Dantas Dias",
    "Moisés dos Santos Silva",
    "Nilton Silva Pereira Junior",
    "Paulo Henrique da Silva de Souza",
    "Pedro Cursino de Oliveira Junior",
    "Pedro Francisco David",
    "Petter Fabio Coutinho da Silva",
    "ROBERTO DIAS DE CARVALHO",
    "Rodrigo Cabral de Souza",
    "Rodrigo Henrique de Souza",
    "Rodrigo Neves Pinto",
    "Rodrigo Pinheiro de Sá",
    "Silvano Ribeiro de Brito",
    "Thiago de Almeida Deulefeu",
    "VALDERI CONSTANTINO CARAMIT",
    "Vitorio Augusto Napoles de Matos",
    "WALTER GEOVANE ZORZETTO DE MORAES",
    "Walerson dos Santos Ferreira",
    "Wallace Vitor Ferreira Silva",
    "Walter Silva de Souza",
    "Wander Araujo de Souza",
    "Wanderson Santos Pequeno",
    "Wilams Vieira",
    "Willian Marques de Almeida",
]

# Índice normalizado para busca rápida
# Chave: nome em lowercase sem acentos simplificado
# Valor: nome exato preferido (primeira ocorrência wins)
import unicodedata

def _normalizar(s: str) -> str:
    s = s.lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s

# Deduplica preferindo a versão com capitalização correta (não uppercase)
_vistos: set = set()
TECNICOS_UNICOS: list[str] = []
for t in TECNICOS:
    chave = _normalizar(t)
    if chave not in _vistos:
        _vistos.add(chave)
        TECNICOS_UNICOS.append(t)

def encontrar_tecnico(nome_busca: str) -> str | None:
    """
    Dado um nome parcial ou apelido, retorna o nome completo
    mais provável da lista oficial.

    Ex:
      "Wallace"        → "Wallace Vitor Ferreira Silva"
      "Michael"        → "Michael Gledson Dantas Dias"
      "Rodrigo Cabral" → "Rodrigo Cabral de Souza"
      "Anderson"       → "Anderson Fernandes de Amorim"
    """
    if not nome_busca:
        return None

    busca_norm = _normalizar(nome_busca)
    palavras_busca = busca_norm.split()

    candidatos = []
    for tecnico in TECNICOS_UNICOS:
        tec_norm = _normalizar(tecnico)
        # Todas as palavras da busca devem estar no nome do técnico
        if all(p in tec_norm for p in palavras_busca):
            candidatos.append(tecnico)

    if len(candidatos) == 1:
        return candidatos[0]
    elif len(candidatos) > 1:
        # Retorna o que tem o menor número de palavras (mais específico)
        return min(candidatos, key=lambda x: len(x.split()))
    return None


def listar_tecnicos() -> list[str]:
    """Retorna lista deduplicada de técnicos."""
    return TECNICOS_UNICOS
