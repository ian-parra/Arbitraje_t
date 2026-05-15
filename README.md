# Arbitraje_t

Dashboard de cotizaciones y calculadora de arbitraje para Argentina.

- **APIs**: DolarApi, ComparaDolar, CriptoYa
- **Tabs**: Perlitas, Billeteras, Bancos, USDT, USDC, Dólares, BRL, Mis Vueltas, Alertas
- **Rutas de arbitraje**: Oficial→MEP, Oficial→Blue, Oficial→CCL, Oficial→USDT→ARS, Oficial→USDC→ARS, USDT→USDC, USDC→USDT, MEP→Blue

## Requisitos

- Python 3.12+
- pip

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python -m streamlit run app.py
```

Abrir en el navegador: `http://localhost:8501`

## Estructura

```
├── app.py               # Aplicación principal Streamlit
├── requirements.txt      # Dependencias
├── .streamlit/
│   └── config.toml       # Tema oscuro de Streamlit
└── data/
    ├── vueltas.json      # Historial de vueltas (persistencia local)
    └── alerts.json       # Alertas de precio (persistencia local)
```
