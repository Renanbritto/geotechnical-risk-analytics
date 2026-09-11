# Geotechnical Risk Analytics

Pipeline analítico geoespacial e motor de inteligência para mapeamento de suscetibilidade a deslizamentos de terra, avaliação de estabilidade de encostas e monitoramento de risco geotécnico em tempo real com integração meteorológica global (Open-Meteo / ECMWF / ERA5-Land).

---

## Visao Geral

O **Geotechnical Risk Analytics** integra técnicas avançadas de geoprocessamento digital, modelagem física de encostas infinitas (*Infinite Slope Stability Model*), processo de análise hierárquica multicritério (*Analytic Hierarchy Process - AHP*) e algoritmos de aprendizado de máquina supervisionado para quantificar e predizer riscos de movimentos de massa em encostas e taludes monitorados.

Projetado em conformidade com as diretrizes do **CEMADEN** (Centro Nacional de Monitoramento e Alertas de Desastres Naturais) e metodologias internacionais de engenharia geotécnica, o sistema permite:

1. **Ingestão Meteorológica em Tempo Real**: Conexão com a API Open-Meteo (modelos ECMWF de alta resolução e ERA5-Land), obtendo precipitação observada acumulada nas últimas 24h e 72h, previsão para as próximas 24h e umidade volumétrica do solo em camadas profundas sem necessidade de chave de API.
2. **Derivação Morfométrica de MDE/DEM**: Cálculo automatizado de declividade (slope), aspecto azimutal, curvatura de vertente e Índice de Umidade Topográfica (TWI).
3. **Modelo Físico de Estabilidade de Encostas**: Cálculo pontual e matricial do Fator de Segurança (FS) geotécnico considerando coesão efetiva do solo, ângulo de atrito interno e poro-pressão d'água.
4. **Ponderação Multicritério AHP (Saaty)**: Matriz de julgamento paritário com validação de consistência matemática (Razão de Consistência CR < 0.10) integrando declividade, pluviometria, litologia e uso/cobertura da terra.
5. **Predição Supervisionada por Machine Learning**: Classificador treinado para categorização de risco em quatro níveis: Baixo, Médio, Alto e Crítico.
6. **API RESTful de Alta Performance (FastAPI)**: Endpoints assíncronos para avaliação em tempo real por coordenadas, processamento em lote e exportação de camadas GeoJSON para GIS (QGIS/ArcGIS).
7. **Cartografia Interativa (Folium/Leaflet)**: Visualização de mapas de calor, setores censitários e alertas hidrológicos com estações virtuais.

---

## Arquitetura do Sistema

```
geotechnical-risk-analytics/
├── .github/
│   └── workflows/
│       └── ci.yml               # Pipeline de CI (Linting e Testes Automatizados)
├── src/
│   ├── api/                     # Camada de Apresentação e API REST (FastAPI)
│   │   ├── routes.py            # Endpoints em tempo real, lote e GeoJSON
│   │   └── server.py            # Inicialização e middlewares da aplicação
│   ├── config/                  # Configurações e variáveis de ambiente
│   │   └── settings.py
│   ├── data/                    # Ingestão e geração de dados geoespaciais
│   │   └── terrain_generator.py # Simulação geoespacial realista de encostas
│   ├── domain/                  # Entidades de domínio e esquemas Pydantic
│   │   ├── models.py
│   │   └── schemas.py
│   ├── geo/                     # Motor de processamento espacial e morfometria
│   │   └── morphometry.py       # Algoritmos de declividade, aspecto e TWI
│   ├── models/                  # Motores de inferência e cálculo geotécnico
│   │   ├── ahp.py               # Analytic Hierarchy Process com checagem CR
│   │   ├── slope_stability.py   # Modelo de encosta infinita e Fator de Segurança
│   │   └── classifier.py        # Modelo supervisionado de Machine Learning
│   ├── services/                # Ingestão meteorológica externa
│   │   └── weather_service.py   # Conector em tempo real Open-Meteo / ECMWF
│   └── visualization/           # Renderização cartográfica interativa
│       └── map_renderer.py      # Mapas de camadas em Folium/Leaflet
├── tests/                       # Suíte de testes automatizados com Pytest (20 testes)
│   ├── test_ahp.py
│   ├── test_slope_stability.py
│   ├── test_morphometry.py
│   ├── test_weather_service.py
│   └── test_api.py
├── docker-compose.yml           # Orquestração de containers para produção
├── Dockerfile                   # Build multi-stage otimizado
├── pyproject.toml               # Metadados e configurações do projeto
├── requirements.txt             # Dependências diretas do projeto
├── main.py                      # CLI interativa para pipelines e servidor
└── README.md                    # Documentação técnica completa
```

---

## Instalação e Execução

### Opção 1: Ambiente Local (Python 3.10+)

```bash
# Clonar o repositório
git clone https://github.com/Renanbritto/geotechnical-risk-analytics.git
cd geotechnical-risk-analytics

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
# No Windows:
.\.venv\Scripts\activate
# No Linux/macOS:
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Opção 2: Execução via Docker / Docker Compose

```bash
# Construir imagem e subir container
docker-compose up --build
```

A API estará disponível em: `http://localhost:8000`
A documentação interativa OpenAPI (Swagger) estará em: `http://localhost:8000/docs`

---

## Comandos da CLI (`main.py`)

O arquivo `main.py` oferece uma interface de linha de comando para automação de tarefas:

```bash
# 1. Avaliar coordenadas em tempo real com dados meteorológicos ao vivo do Open-Meteo
python main.py --eval-live --lat -22.4200 --lon -42.9700 --slope 35.0

# 2. Executar pipeline analítico completo e gerar mapa interativo
python main.py --run-pipeline

# 3. Iniciar servidor da API REST
python main.py --serve-api --port 8000

# 4. Executar suíte completa de testes automatizados
python main.py --run-tests
```

---

## Endpoints Principais da API REST

| Método | Rota | Descrição |
| :--- | :--- | :--- |
| `GET` | `/health` | Status de saúde da aplicação |
| `GET` | `/api/v1/weather/live` | Dados meteorológicos ao vivo para coordenada (chuva 24h/72h e umidade do solo) |
| `GET` | `/api/v1/risk/evaluate-live` | Avaliação geotécnica instantânea com clima ao vivo |
| `POST` | `/api/v1/risk/evaluate-point` | Avaliação detalhada de ponto parametrizado |
| `POST` | `/api/v1/risk/batch-assessment` | Processamento analítico em lote |
| `GET` | `/api/v1/risk/ahp-consistency` | Auditoria matemática da consistência de Saaty |
| `GET` | `/api/v1/spatial/geojson` | Exportação de camada GeoJSON vetorial para QGIS |
| `GET` | `/api/v1/spatial/map-html` | Renderização do mapa Leaflet direto no navegador |

---

## Metodologia e Formulações Matemáticas

### 1. Fator de Segurança (FS) - Modelo de Encosta Infinita
Para uma encosta translacional com nível freático paralelo à superfície:

$$FS = \frac{c' + (\gamma_{sat} \cdot z - \gamma_w \cdot h_w) \cdot \cos^2(\beta) \cdot \tan(\phi')}{\gamma_{sat} \cdot z \cdot \sin(\beta) \cdot \cos(\beta)}$$

Onde:
- $c'$: Coesão efetiva do solo (kPa)
- $\phi'$: Ângulo de atrito interno do solo (graus)
- $\beta$: Declividade da encosta (graus)
- $z$: Profundidade do plano de ruptura (m)
- $h_w$: Altura do nível freático acima da superfície de ruptura (m), modulado por chuva e umidade volumétrica
- $\gamma_{sat}$: Peso específico saturado do solo ($\text{kN/m}^3$)
- $\gamma_w$: Peso específico da água ($9.81\ \text{kN/m}^3$)

Classificação geotécnica:
- $FS > 1.5$: Estável (Risco Baixo)
- $1.2 \le FS \le 1.5$: Marginalmente estável (Risco Médio)
- $1.0 \le FS < 1.2$: Iminência de ruptura (Risco Alto)
- $FS < 1.0$: Instável / Ruptura ativa (Risco Crítico)

### 2. Matriz AHP e Razão de Consistência (CR)
O Analytic Hierarchy Process de Thomas Saaty estabelece uma matriz de comparação pareada $A = [a_{ij}]$. O autovetor principal fornece o vetor de pesos normalizados $w$.
O Índice de Consistência ($CI$) e a Razão de Consistência ($CR$) são calculados por:

$$CI = \frac{\lambda_{max} - n}{n - 1}, \quad CR = \frac{CI}{RI}$$

Onde $RI$ é o Índice Randômico tabelado ($RI_{n=4} = 0.90$). Um valor de $CR < 0.10$ certifica a coerência lógica dos pesos atribuídos.

---

## Testes Automatizados

Para executar os 20 testes com métricas de assertividade:

```bash
pytest -v tests/
```

---

## Licença

Este projeto é distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
