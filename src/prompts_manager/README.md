# Gerenciador de Prompts

Aplicação local em Flask para criar, versionar e consultar prompts usados pelo
`media_generator_graph`. Cada versão é persistida em JSON no sistema de
arquivos, com metadados do modelo e um ponteiro para a versão ativa de cada
prompt.

O módulo é independente da execução do grafo: ele administra os arquivos de
prompt; não chama modelos nem executa o LangGraph.

## Funcionalidades

- Criação de prompts e de novas versões pela interface web.
- Versionamento semântico no formato `vMAJOR.MINOR.PATCH`.
- Ativação de uma versão anterior, com descontinuação automática da que estava
  ativa.
- Histórico de versões, ordenado da mais recente para a mais antiga.
- Registro do conteúdo, modelo, temperatura, esforço de raciocínio, autor,
  nota da alteração, data de criação e status de cada versão.
- Proteção CSRF nos formulários e validação do nome do prompt contra traversal
  de caminho.
- Persistência local sem banco de dados.

## Requisitos

- Python 3.13 ou superior.
- [`uv`](https://docs.astral.sh/uv/).

As dependências próprias do módulo são `Flask` e `Flask-WTF`. No repositório,
ele é um membro do workspace `uv`.

## Instalação e execução

Execute os comandos a partir da raiz do repositório:

```bash
uv sync
cp src/prompts_manager/.env.example src/prompts_manager/.env
PYTHONPATH=src uv run python -m prompts_manager.backend
```

O servidor inicia, por padrão, em [http://127.0.0.1:5000](http://127.0.0.1:5000).
Ele fica vinculado somente a `127.0.0.1`; não é exposto à rede.

> O arquivo `.env` pertence ao diretório `src/prompts_manager/`. O módulo o
> carrega automaticamente, independentemente do diretório de onde o comando é
> iniciado.

## Configuração

Use [`src/prompts_manager/.env.example`](.env.example) como ponto de partida.

| Variável | Padrão | Finalidade |
| --- | --- | --- |
| `ENVIRONMENT_PROMPT_MANAGER` | `development` | Ambiente de execução. Em `production`, `FLASK_DEBUG=true` impede a inicialização. |
| `PROMPT_DIR` | `agents/prompts` | Diretório que armazena prompts e `metadata.json`. Caminhos relativos são resolvidos a partir de `src/media_generator_graph/`. |
| `MAX_PROMPT_SIZE` | `100_000` | Tamanho máximo do conteúdo do prompt, em bytes UTF-8. |
| `PROMPT_MANAGER_PORT` | `5000` | Porta do servidor Flask local. |
| `FLASK_SECRET_KEY` | não definida | Chave de sessão usada pelo Flask/CSRF. Defina um valor secreto fora do controle de versão. |
| `FLASK_DEBUG` | `false` | Ativa o modo de depuração do Flask. Nunca use com `ENVIRONMENT_PROMPT_MANAGER=production`. |
| `PROMPT_MANAGER_SERVER_TIMEZONE` | `UTC` | Fuso usado para exibir datas na interface, por exemplo `America/Sao_Paulo`. |

`PROMPT_DIR` deve apontar para um diretório gravável. Se não existir, a
aplicação o cria junto com o `metadata.json` inicial. O processo também faz uma
verificação de escrita ao criar a aplicação.

Exemplo para apontar explicitamente para os prompts do grafo:

```env
PROMPT_DIR=agents/prompts
PROMPT_MANAGER_SERVER_TIMEZONE=America/Sao_Paulo
FLASK_SECRET_KEY=troque-por-uma-chave-secreta
```

## Uso pela interface

1. Abra `http://127.0.0.1:5000`.
2. Em **Novo prompt**, informe nome, conteúdo, modelo, autor e nota da
   alteração. Temperatura e esforço de raciocínio são opcionais.
3. Escolha o tipo de incremento:
   - `patch`: correção incremental, como `v1.0.0` → `v1.0.1`;
   - `minor`: mudança compatível ou relevante, como `v1.0.1` → `v1.1.0`;
   - `major`: mudança que exige uma nova linha principal, como `v1.1.0` →
     `v2.0.0`.
4. A primeira versão é criada como `v1.0.0` e se torna ativa.
5. Para um prompt já existente, abra-o na lista e crie uma nova versão. A nova
   versão passa a ser a ativa, e a anterior recebe o status `deprecated`.
6. Para retornar a uma versão existente, use **Ativar** no histórico. A versão
   escolhida volta a ser `active` e a anteriormente ativa é descontinuada.

Os nomes aceitos têm até 64 caracteres, começam por letra ou número e podem
conter letras, números, hífen (`-`) e sublinhado (`_`). Exemplos válidos:
`linkedin_post`, `yt-script` e `x_thread_v2`.

## Formato de armazenamento

O diretório configurado é organizado assim:

```text
<PROMPT_DIR>/
├── metadata.json
└── linkedin_post/
    ├── v1.0.0.json
    └── v1.1.0.json
```

`metadata.json` mantém somente o ponteiro da versão ativa de cada prompt:

```json
{
  "active_versions": {
    "linkedin_post": "v1.1.0"
  }
}
```

Cada arquivo de versão contém o registro completo. Exemplo:

```json
{
  "prompt_name": "linkedin_post",
  "prompt_version": "v1.1.0",
  "prompt_content": "Escreva uma publicação objetiva para LinkedIn.",
  "llm_model": "openai/gpt-5.4-mini",
  "llm_temperature": 0.2,
  "llm_reasoning_effort": "medium",
  "owner": "Fellipe",
  "change_note": "Ajusta a abertura e a chamada para ação.",
  "created_at": "2026-09-30T12:00:00+00:00",
  "status": "active"
}
```

Os status atualmente usados são `active` e `deprecated`. A operação de
ativação preserva o histórico: ela não apaga arquivos, apenas atualiza os dois
status envolvidos e o ponteiro em `metadata.json`.

## Modelos disponíveis na interface

A lista é fixa no código em
[`backend/llm_models.py`](backend/llm_models.py). No estado atual, inclui
modelos OpenAI, Google, DeepSeek, MiniMax e GLM disponibilizados pelo
OpenRouter. O campo apenas registra o identificador selecionado na versão; o
Gerenciador de Prompts não executa chamadas à API do provedor.

## Estrutura do módulo

```text
src/prompts_manager/
├── backend/
│   ├── __main__.py          # valida configuração e inicia o servidor
│   ├── prompt_store.py      # cria arquivos de versão e altera a versão ativa
│   ├── prompt_reads.py      # lista e lê prompts/versões
│   ├── version_lifecycle.py # ativa ou descontinua versões
│   ├── version_parse.py     # regras de versão semântica
│   ├── version_queries.py   # consulta o histórico ordenado
│   ├── metadata_store.py    # lê e grava metadata.json com lock de arquivo
│   └── llm_models.py        # catálogo de IDs de modelos
├── frontend/
│   ├── app.py               # rotas Flask e composição da interface
│   └── templates/           # páginas Jinja2
├── shared/
│   ├── settings.py          # variáveis de ambiente e resolução de caminhos
│   └── prompts_directory.py # criação e validação de diretórios
└── .env.example
```

## Operações disponíveis no código

Além da interface, o backend expõe funções Python para uso interno:

```python
from prompts_manager.backend.prompt_reads import load_prompt_version
from prompts_manager.backend.prompt_store import create_prompt_version
from prompts_manager.backend.version_lifecycle import set_active_version

version = create_prompt_version(
    prompt_name="linkedin_post",
    prompt_content="Escreva uma publicação objetiva para LinkedIn.",
    model="openai/gpt-5.4-mini",
    owner="Fellipe",
    change_note="Versão inicial.",
    change_type="minor",
    temperature=0.2,
    reasoning_effort="medium",
)

active = load_prompt_version("linkedin_post")
set_active_version("linkedin_post", version)
```

Quando `load_prompt_version()` é chamada sem uma versão, ela tenta usar a
registrada em `metadata.json`. Se não houver ponteiro ativo, retorna a versão
semântica mais recente disponível.

## Testes e verificações

Na raiz do repositório:

```bash
PYTHONPATH=src uv run pytest tests/unit/prompts_manager -q
PYTHONPATH=src uv run ruff check src/prompts_manager tests/unit/prompts_manager
PYTHONPATH=src uv run ruff format --check src/prompts_manager tests/unit/prompts_manager
PYTHONPATH=src uv run pyright src/prompts_manager
```

Os testes de unidade usam diretórios temporários e não alteram o diretório de
prompts configurado para a aplicação.

## Limitações conhecidas

- A interface depende do CDN do Tailwind CSS; por isso, o estilo não é
  totalmente autossuficiente sem acesso ao CDN.
- A rota web de descontinuação de versão requer correção antes de ser usada:
  em `frontend/app.py`, a função de rota tem o mesmo nome da função de domínio
  importada e acaba chamando a si própria. Criar, consultar e ativar versões
  continuam sendo fluxos separados dessa limitação.
- A checagem atual com Pyright reporta uma incompatibilidade de tipo em
  `backend/version_parse.py`: a função auxiliar pode retornar tanto uma lista
  de tuplas quanto a string `"v1.0.0"`. Isso é uma pendência do código, não do
  README.
- O armazenamento é local em arquivos JSON. Ele não oferece histórico de
  auditoria além dos próprios arquivos de versão nem coordenação distribuída.

## Segurança operacional

- Não versione `src/prompts_manager/.env` nem exponha `FLASK_SECRET_KEY`.
- Mantenha o servidor em `127.0.0.1`, como configurado pelo entrypoint.
- Use permissões de arquivo adequadas no diretório definido por `PROMPT_DIR`,
  pois ele contém o conteúdo integral dos prompts.
- Faça cópias de segurança do diretório de prompts antes de alterações manuais
  nos arquivos JSON.
