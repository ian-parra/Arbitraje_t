import streamlit as st
import requests
import json
import os
import pandas as pd
import plotly.express as px
from datetime import datetime
import uuid

st.set_page_config(page_title="CambioAR · Cotizaciones", layout="wide", page_icon="💱")

DOLARAPI = "https://dolarapi.com/v1"
CDOLAR = "https://api.comparadolar.ar/api/v1"
CRIPTOYA = "https://criptoya.com/api"
DATA_DIR = "data"
VUELTAS_FILE = os.path.join(DATA_DIR, "vueltas.json")
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
WALLET_SLUGS = {'plus','plus-crypto','plus-inversiones','reba','tiendadolar','wallbit','nexo','lemon','belo','prex'}
CRYPTOYA_TO_CDOLAR = {'bbva':'bbva','bna':'banco-nacion','brubank':'brubank','hipotecario':'banco-hipotecario','supervielle':'banco-supervielle','pluscambio':'plus','prex':'prex'}
BANK_NAMES = {'andina':'Banco Andina','bapro':'Banco BAPRO','ciudad':'Banco Ciudad','columbia':'Banco Columbia','comafi':'Banco Comafi','galicia':'Banco Galicia','icbc':'ICBC','macro':'Banco Macro','mariva':'Banco Mariva','patagonia':'Banco Patagonia','piano':'Banco Piano','plazacambio':'Plaza Cambio','santander':'Banco Santander','triacambio':'Triacambio','bytelime':'Tienda Dólar','bna':'Banco Nación','hipotecario':'Banco Hipotecario','supervielle':'Banco Supervielle','bbva':'BBVA','brubank':'Brubank','pluscambio':'Plus Cambio','prex':'PREX'}
CCL_SLUGS = ['plus-crypto','plus-inversiones','cocos','nexo','wallbit']

def load_json(path, default=None):
    if default is None: default = []
    try:
        if os.path.exists(path):
            with open(path) as f: return json.load(f)
    except: pass
    return default

def save_json(path, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(path, 'w') as f: json.dump(data, f, indent=2)

@st.cache_data(ttl=120)
def get(url):
    try:
        r = requests.get(url, timeout=15); return r.json()
    except: return {}

def fmt(v):
    if v is None or v == 0: return '—'
    return f"${v:,.2f}"

def fmt_short(v):
    if v is None or v == 0: return '—'
    return f"${v:,.0f}"

def render_arb_card(route, steps, gain_pct, gain_pesos, time_val, risk, buy, sell, idx, conv=None):
    pos = gain_pct >= 0
    risk_colors = {'low':'#29e8a0','mid':'#f5b946','high':'#f2566b'}
    risk_labels = {'low':'Bajo riesgo','mid':'Riesgo medio','high':'Alto riesgo'}
    return {
        'route':route, 'steps':steps, 'gain_pct':gain_pct, 'gain_pesos':gain_pesos,
        'time':time_val, 'risk':risk, 'risk_label':risk_labels.get(risk,''),
        'risk_color':risk_colors.get(risk,'#484a5c'),
        'buy':buy, 'sell':sell, 'pos':pos, 'idx':idx, 'conv':conv
    }

def fmt_ars(v):
    if not v and v!=0: return '—'
    return f"${v:,.2f}".replace(',','X').replace('.',',').replace('X','.')

def fmt_pct(v):
    return f"{'+' if v>=0 else ''}{v:.3f}%"

def calc_vuelta(v):
    usd = v['pesosInicial'] / v['cotizacionCompra']
    usdc = usd * v['tasaConversion'] * (1 - v['comisionPct']/100)
    ars = usdc * v['precioVenta']
    gan = ars - v['pesosInicial']
    pct = gan / v['pesosInicial'] * 100
    return usd, usdc, ars, gan, pct

# ── Init ──
if 'vueltas' not in st.session_state:
    st.session_state.vueltas = load_json(VUELTAS_FILE)
if 'alerts' not in st.session_state:
    st.session_state.alerts = load_json(ALERTS_FILE)

# ── Title ──
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #0f1016; border: 1px solid rgba(255,255,255,.06); border-radius: 10px; padding: 4px; margin-bottom: 22px; }
.stTabs [data-baseweb="tab"] { padding: 7px 14px; border-radius: 7px; font-size: 13px; font-weight: 500; background: transparent; color: #858699; }
.stTabs [aria-selected="true"] { background: #1d1f2b; border: 1px solid rgba(255,255,255,.11); color: #ecedf5; }
div[data-testid="stMetric"] { background: #161720; border: 1px solid rgba(255,255,255,.06); border-radius: 10px; padding: 12px; }
div[data-testid="stMetric"] label { color: #858699; font-size: 11px; font-family: 'JetBrains Mono', monospace; }
div[data-testid="stMetric"] div { color: #ecedf5 !important; }
.stButton button { background: #1d1f2b; border: 1px solid rgba(255,255,255,.11); color: #ecedf5; border-radius: 8px; font-size: 12px; }
.stButton button:hover { border-color: rgba(255,255,255,.18); }
.stNumberInput input { background: #1d1f2b; border: 1px solid rgba(255,255,255,.11); color: #ecedf5; border-radius: 8px; font-family: 'JetBrains Mono', monospace; }
.stDataFrame { font-size: 12px !important; }
hr { margin: 0 !important; border-color: rgba(255,255,255,.06) !important; }
.badge { display: inline-block; background: rgba(93,168,255,.12); border: 1px solid rgba(93,168,255,.3); border-radius: 4px; padding: 1px 6px; font-size: 9px; color: #5da8ff; font-family: 'JetBrains Mono', monospace; margin-left: 4px; }
.best { color: #29e8a0 !important; font-weight: 600; }
.worst { color: #f2566b !important; }
.gain { color: #29e8a0; }
.loss { color: #f2566b; }
.error-badge { display: inline-block; background: rgba(242,86,107,.12); border: 1px solid rgba(242,86,107,.3); border-radius: 4px; padding: 1px 6px; font-size: 9px; color: #f2566b; font-family: 'JetBrains Mono', monospace; }
</style>
""", unsafe_allow_html=True)

st.title("CambioAR", anchor=False)

# ── Sidebar config ──
st.sidebar.markdown("### ⚙️ Configuración")
if st.sidebar.button("🔄 Refrescar datos", use_container_width=True, type="primary"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption("Limpia caché y vuelve a consultar APIs")

# ── Last updated ──
_ts = datetime.now()
st.sidebar.markdown("---")
st.sidebar.caption(f"🕐 Actualizado: {_ts.strftime('%H:%M:%S')}")

# ════════════════════════════════════════
# FETCH ALL DATA
# ════════════════════════════════════════
with st.spinner("Cargando cotizaciones..."):
    d_oficial = get(f"{DOLARAPI}/dolares/oficial")
    d_blue = get(f"{DOLARAPI}/dolares/blue")
    d_mep = get(f"{DOLARAPI}/dolares/bolsa")
    d_ccl = get(f"{DOLARAPI}/dolares/contadoconliquidacion")
    d_cotizaciones = get(f"{DOLARAPI}/cotizaciones")
    cd_wallets = get(f"{CDOLAR}/usd")
    c_usdt_ars = get(f"{CRIPTOYA}/USDT/ARS/1")
    c_usdc_ars = get(f"{CRIPTOYA}/USDC/ARS/1")
    c_usdc_usd = get(f"{CRIPTOYA}/USDC/USD/1")
    cy_bancos = get(f"{CRIPTOYA}/bancostodos")

o_venta = d_oficial.get('venta',0) or 0
o_compra = d_oficial.get('compra',0) or 0
blue_compra = d_blue.get('compra',0) or 0
mep_compra = d_mep.get('compra',0) or 0
ccl_compra = d_ccl.get('compra',0) or 0
eur_data = next((c for c in d_cotizaciones if isinstance(c,dict) and c.get('moneda')=='EUR'),{}) if isinstance(d_cotizaciones,list) else {}
eur_venta = eur_data.get('venta',0) or 0
eur_compra = eur_data.get('compra',0) or 0

usdt_ex = [{'slug':s,'name':s[0].upper()+s[1:].replace('p2p',' P2P'),'bid':d.get('bid',0) or 0,'ask':d.get('ask',0) or 0}
    for s,d in c_usdt_ars.items() if isinstance(d,dict) and (d.get('bid',0) or 0)>0 and s not in ('wexx','weeexp2p')]
usdc_ex = [{'slug':s,'name':s[0].upper()+s[1:].replace('p2p',' P2P'),'bid':d.get('bid',0) or 0,'ask':d.get('ask',0) or 0}
    for s,d in c_usdc_ars.items() if isinstance(d,dict) and (d.get('bid',0) or 0)>0]

usdc_usd_rates = {s:d.get('ask',0) for s,d in c_usdc_usd.items() if isinstance(d,dict) and d.get('ask',0)>0}

best_usdt_sell = max(usdt_ex, key=lambda x:x['bid']) if usdt_ex else None
best_usdt_buy = min([x for x in usdt_ex if x['ask']>0], key=lambda x:x['ask']) if any(x['ask']>0 for x in usdt_ex) else None
best_usdc_sell = max(usdc_ex, key=lambda x:x['bid']) if usdc_ex else None
best_usdc_buy = min([x for x in usdc_ex if x['ask']>0], key=lambda x:x['ask']) if any(x['ask']>0 for x in usdc_ex) else None

usdc_usd_best = sorted([(s,d['ask']) for s,d in c_usdc_usd.items() if isinstance(d,dict) and d.get('ask',0)>0], key=lambda x:x[1])
best_usdc_usd_rate = usdc_usd_best[0][1] if usdc_usd_best else 1.0
best_usdc_usd_name = usdc_usd_best[0][0][0].upper()+usdc_usd_best[0][0][1:].replace('p2p',' P2P') if usdc_usd_best else 'Binance'

tabs = st.tabs(["💎 Perlitas","📊 Mis Vueltas","🔔 Alertas"])

# Global default for sell price used across tabs
default_venta = best_usdc_sell['bid'] if best_usdc_sell else 1450.0

# ════════════════════════════════════════
# TAB 0: PERLITAS
# ════════════════════════════════════════
with tabs[0]:

    # ── ARBITRAGE ROUTES ──
    st.markdown("##### Rutas de arbitraje")
    arb_amt = st.number_input("Monto ARS", value=1_000_000, step=100_000, format="%d", key="arb_amt")

    routes = []

    # 1. Oficial → MEP
    if o_venta>0 and mep_compra>0:
        pct = (mep_compra-o_venta)/o_venta*100
        routes.append(render_arb_card('Oficial → MEP',
            ['Comprás USD al oficial','Vendés USD en bolsa (MEP)','Esperás 24-48hs parking'],
            pct, mep_compra-o_venta, '24-48hs', 'mid', o_venta, mep_compra, 0))

    # 2. Oficial → Blue
    if o_venta>0 and blue_compra>0:
        pct = (blue_compra-o_venta)/o_venta*100
        routes.append(render_arb_card('Oficial → Blue',
            ['Comprás USD al oficial','Vendés al contado (blue)','Operás en cueva/P2P — riesgo contraparte'],
            pct, blue_compra-o_venta, 'Inmediato', 'high', o_venta, blue_compra, 1))

    # 3. Oficial → CCL
    if o_venta>0 and ccl_compra>0:
        pct = (ccl_compra-o_venta)/o_venta*100
        routes.append(render_arb_card('Oficial → CCL',
            ['Comprás USD al oficial','Vendés contado con liquidación','Esperás 24-48hs settlement'],
            pct, ccl_compra-o_venta, '24-48hs', 'mid', o_venta, ccl_compra, 2))

    # 4. Oficial → USDT → ARS
    if o_venta>0 and best_usdt_sell and best_usdt_buy:
        ratio = best_usdt_buy['ask'] / o_venta
        eff = best_usdt_buy['ask']
        pct = (best_usdt_sell['bid']/eff-1)*100
        routes.append(render_arb_card('Oficial → USDT → ARS',
            [f'Comprás USD al oficial',f'Convertís USD→USDT en {best_usdt_buy["name"]} (ratio {ratio:.3f})',f'Vendés USDT a {fmt(best_usdt_sell["bid"])} en {best_usdt_sell["name"]}'],
            pct, best_usdt_sell['bid']-eff, 'Inmediato', 'mid', o_venta, best_usdt_sell['bid'], 3, {'ratio':ratio}))

    # 4b. Oficial → USDC → ARS
    if o_venta>0 and best_usdc_sell and best_usdc_usd_rate>0:
        ratio = best_usdc_usd_rate
        eff = o_venta * ratio
        pct = (best_usdc_sell['bid']/eff-1)*100
        routes.append(render_arb_card('Oficial → USDC → ARS',
            ['Comprás USD al oficial',f'Depositás en {best_usdc_usd_name} → USDC (ratio {ratio:.4f})',f'Vendés USDC a {fmt(best_usdc_sell["bid"])} en {best_usdc_sell["name"]}'],
            pct, best_usdc_sell['bid']-eff, '1-3 días', 'mid', o_venta, best_usdc_sell['bid'], 4, {'ratio':ratio}))

    # 7. MEP → Blue
    if mep_compra>0 and blue_compra>0:
        pct = (blue_compra/mep_compra-1)*100
        routes.append(render_arb_card('MEP → Blue',
            ['Comprás USD en bolsa (MEP)','Vendés al contado (blue)','Esperás 24-48hs MEP + blue inmediato'],
            pct, blue_compra-mep_compra, '24-48hs', 'high', mep_compra, blue_compra, 7))

    # Sort by gain pct descending
    routes.sort(key=lambda r: r['gain_pct'], reverse=True)

    if routes:
        pos_routes = [r for r in routes if r['gain_pct'] >= 0]
        neg_routes = [r for r in routes if r['gain_pct'] < 0]

        def render_route_card(r, arb_amt):
            gs = r['gain_pct']
            pos = gs >= 0
            color = '#29e8a0' if pos else '#f2566b'
            if not pos:
                st.markdown(f"""
<div style="background:#0f1016;border:1px solid rgba(242,86,107,.12);border-radius:14px;padding:14px;margin-bottom:10px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
<span style="font-size:12px;font-weight:600">{r['route']}</span>
<span style="font-family:monospace;font-size:16px;font-weight:700;color:#f2566b">{gs:.2f}%</span>
</div>
<div style="font-size:11px;color:#858699;margin-bottom:6px">{r['steps'][0]}<br>{r['steps'][1]}<br>{r['steps'][2]}</div>
<div style="display:flex;justify-content:space-between;align-items:center">
<span style="background:rgba(242,86,107,.12);color:#f2566b;border:1px solid rgba(242,86,107,.3);border-radius:6px;padding:2px 10px;font-size:11px;font-weight:600">❌ No rinde</span>
<span style="font-size:9px;color:#858699">⏱ {r['time']}</span>
</div>
</div>
""", unsafe_allow_html=True)
                return
            usd = arb_amt / r['buy'] if r['buy'] > 0 else 0
            if r['conv'] and r['conv'].get('ratio'):
                usdt_amt = usd / r['conv']['ratio']
                final = usdt_amt * r['sell'] if r['sell'] > 0 else 0
            else:
                usdt_amt = None
                final = usd * r['sell'] if r['sell'] > 0 else 0
            diff = final - arb_amt
            color = '#29e8a0' if pos else '#f2566b'
            cols_grid = '1fr 1fr 1fr' if not usdt_amt else '1fr 1fr 1fr 1fr'
            obten_val = f"{usdt_amt:.2f} USDT/USDC" if usdt_amt else f"{usd:.0f} USD"
            st.markdown(f"""
<div style="background:#0f1016;border:1px solid {'rgba(41,232,160,.15)' if pos else 'rgba(242,86,107,.12)'};border-radius:14px;padding:16px;margin-bottom:10px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
<span style="font-size:12px;font-weight:600">{r['route']}</span>
<span style="font-family:monospace;font-size:18px;font-weight:700;color:{color}">{'+' if pos else ''}{gs:.2f}%</span>
</div>
<div style="font-size:11px;color:#858699;margin-bottom:8px">
{r['steps'][0]}<br>
{r['steps'][1]}<br>
{r['steps'][2]}
</div>
<div style="background:#1d1f2b;border-radius:10px;padding:10px;margin-bottom:8px">
<div style="display:grid;grid-template-columns:{cols_grid};gap:6px;text-align:center">
<div><div style="font-size:9px;color:#484a5c">Invertís</div><div style="font-size:13px;font-weight:600">{fmt_short(arb_amt)}</div></div>
<div><div style="font-size:9px;color:#484a5c">Obtenés</div><div style="font-size:13px;font-weight:600;color:#f5b946">{obten_val}</div></div>
{f'<div><div style="font-size:9px;color:#484a5c">USDT/USDC</div><div style="font-size:13px;font-weight:600;color:#a78bfa">{usdt_amt:.2f}</div></div>' if usdt_amt else ''}
<div><div style="font-size:9px;color:#484a5c">Recibís</div><div style="font-size:13px;font-weight:600;color:#5da8ff">{fmt_short(final)}</div></div>
</div>
<div style="margin-top:6px;padding-top:4px;border-top:1px solid rgba(255,255,255,.06);text-align:center">
<span style="font-size:11px;color:#484a5c">Ganancia: </span>
<span style="font-size:14px;font-weight:700;color:{'#29e8a0' if diff>=0 else '#f2566b'}">{'+' if diff>=0 else ''}{fmt_short(diff)}</span>
{f'<div style="font-size:9px;color:#858699;margin-top:2px">ℹ️ Spread negativo — la ruta genera pérdida. Buscá mejor cotización.</div>' if not pos else ''}
</div>
</div>
<div style="display:flex;justify-content:space-between;font-size:9px;color:#858699">
<span>⏱ {r['time']}</span>
<span style="color:{r['risk_color']}">⚠ {r['risk_label']}</span>
</div>
</div>
""", unsafe_allow_html=True)

        all_routes = pos_routes + neg_routes
        cols = st.columns(2)
        for i, r in enumerate(all_routes):
            with cols[i % 2]:
                render_route_card(r, arb_amt)
    else:
        st.info("No se detectaron oportunidades de arbitraje rentables.")

    st.divider()

    # ── USD → USDC/USDT Calculator ──
    st.markdown("##### Calculadora USD → USDC/USDT → ARS")

    # ── USD→USDC rate selector (buy side) ──
    buy_opts = {}
    if isinstance(c_usdc_usd, dict):
        items = [(slug, d) for slug, d in c_usdc_usd.items() if isinstance(d, dict) and d.get('ask', 0) > 0]
        items.sort(key=lambda x: x[1]['ask'])
        min_ask = items[0][1]['ask'] if items else 1.0
        for slug, d in items:
            name = slug[0].upper() + slug[1:].replace('p2p', ' P2P')
            rate = 1.0 / d['ask']
            star = "⭐ " if d['ask'] == min_ask else ""
            buy_opts[f"{star}{name} ({rate:.4f})"] = rate
    buy_opts["✏️  Manual"] = 0.9527
    buy_names = list(buy_opts.keys())
    buy_default = next((i for i, w in enumerate(buy_names) if '⭐' in w), len(buy_names) - 1)

    # ── USDC/USDT→ARS sell side selector ──
    sell_opts = {}
    seen = set()
    for ex_list in [usdc_ex, usdt_ex]:
        for x in ex_list:
            slug = x['slug']
            if slug not in seen and x.get('bid', 0) > 0:
                seen.add(slug)
                sell_opts[f"{x['name']} (${x['bid']:.2f})"] = x['bid']
    sell_items = sorted(sell_opts.items(), key=lambda kv: -kv[1])
    sell_names = [k for k, v in sell_items]
    sell_vals = [v for k, v in sell_items]
    sell_default = 0

    st.markdown("""
    <div style="background:#0f1016;border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:18px;margin:10px 0">
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        fci_usd = st.number_input("💵 USD comprados", value=1000.0, step=100.0, format="%.2f", key="fci_usd", help="Cantidad de dólares que compraste al oficial")
        fci_oficial = st.number_input("🇦🇷 Cotización oficial (ARS/USD)", value=float(o_venta or 1405), step=1.0, key="fci_oficial", help="Ej: 1405")
    with c2:
        sel_wallet = st.selectbox("🏦 Comprar USDC/USDT en", options=buy_names, index=buy_default, key="sel_buy", help="Exchange para convertir USD→USDC/USDT. Seleccioná uno o elegí Manual")
        is_manual = "Manual" in sel_wallet
        if is_manual:
            fci_tasa = st.number_input("🔄 Tasa USD→USDC/USDT (manual)", value=buy_opts.get(sel_wallet, 0.9527), step=0.001, format="%.4f", key="fci_tasa_manual", help="Cuántos USDC/USDT recibís por USD. Usá 1.0 si no hay conversión de por medio.")
        else:
            fci_tasa = buy_opts.get(sel_wallet, 0.9527)
        sell_idx = st.selectbox("💱 Vender USDC/USDT en", options=range(len(sell_names)), format_func=lambda i: sell_names[i], index=sell_default, key="sel_sell", help="Exchange que compra tus stablecoins al mejor precio. Ordenado de mejor a peor bid.")
        fci_venta = sell_vals[sell_idx]

    st.markdown("</div>", unsafe_allow_html=True)

    inv = fci_usd * fci_oficial
    rec = fci_usd * fci_tasa
    ars_rec = rec * fci_venta
    gan = ars_rec - inv
    gan_pct = gan/inv*100 if inv>0 else 0
    gan_color = "#29e8a0" if gan >= 0 else "#f2566b"

    st.markdown(f"""
    <div style="background:#0f1016;border:1px solid rgba(255,255,255,.06);border-radius:14px;padding:18px;margin:10px 0">
    <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;text-align:center">
    <div><div style="font-size:10px;color:#484a5c;margin-bottom:4px">Invertiste (ARS)</div><div style="font-size:16px;font-weight:700">{fmt_short(inv)}</div></div>
    <div><div style="font-size:10px;color:#484a5c;margin-bottom:4px">Recibís USDC/USDT</div><div style="font-size:16px;font-weight:700;color:#f5b946">{rec:.2f}</div></div>
    <div><div style="font-size:10px;color:#484a5c;margin-bottom:4px">ARS al vender</div><div style="font-size:16px;font-weight:700;color:#5da8ff">{fmt_short(ars_rec)}</div></div>
    <div><div style="font-size:10px;color:#484a5c;margin-bottom:4px">Ganancia</div><div style="font-size:16px;font-weight:700;color:{gan_color}">{'+' if gan>=0 else ''}{fmt_short(gan)} ({gan_pct:.2f}%)</div></div>
    </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════
# ════════════════════════════════════════
# TAB 1: MIS VUELTAS
# ════════════════════════════════════════
with tabs[1]:
    st.markdown("### 📊 Mis Vueltas")

    # Form always visible at top
    with st.expander("➕ Nueva vuelta", expanded=True):
        with st.form("vuelta_form", clear_on_submit=True):
            c1,c2 = st.columns(2)
            with c1:
                f_pesos = st.number_input("Inversión (ARS)", value=1_000_000.0, step=100_000.0, format="%.2f")
                f_cotizacion = st.number_input("Cotización compra USD oficial", value=float(o_venta or 1400), step=1.0)
                f_tasa = st.number_input("Tasa USD→USDC/USDT", value=0.9527, step=0.001, format="%.4f", help="Ej: Lemon cobra ~4.7%, tasa ~0.9527. Si no usás stablecoin, poné 1.0")
            with c2:
                f_comision = st.number_input("Comisión del exchange %", value=0.50, step=0.01, format="%.2f", help="Comisión que te cobra el exchange al vender (ej: 0.5%)")
                f_venta = st.number_input("Precio venta USDC/USDT (ARS)", value=float(default_venta), step=1.0)
                f_exchange = st.text_input("Exchange", value="Lemon")
            f_fecha = st.date_input("Fecha", value=datetime.now())

            if st.form_submit_button("💾 Guardar vuelta"):
                v = {
                    'id': str(uuid.uuid4())[:8],
                    'fecha': f_fecha.strftime("%Y-%m-%d"),
                    'pesosInicial': f_pesos,
                    'cotizacionCompra': f_cotizacion,
                    'tasaConversion': f_tasa,
                    'comisionPct': f_comision,
                    'precioVenta': f_venta,
                    'exchange': f_exchange
                }
                st.session_state.vueltas.append(v)
                save_json(VUELTAS_FILE, st.session_state.vueltas)
                st.rerun()

    vueltas = st.session_state.vueltas
    if not vueltas:
        st.info("Todavía no registraste ninguna vuelta.")
    else:
        # Stats
        pcts = []; total_in = 0; total_out = 0
        best_idx = 0; best_p = -999
        for i, v in enumerate(vueltas):
            _, _, ars, gan, p = calc_vuelta(v)
            pcts.append(p)
            total_in += v['pesosInicial']
            total_out += ars
            if p > best_p: best_p = p; best_idx = i

        k1,k2,k3,k4 = st.columns(4)
        with k1: st.metric("Vueltas", str(len(vueltas)))
        with k2: st.metric("Promedio %", f"{np.mean(pcts):.3f}%" if pcts else '—')
        with k3: st.metric("Total invertido", fmt_short(total_in))
        with k4:
            gan_total = total_out - total_in
            st.metric("Ganancia total", f"{'+' if gan_total>=0 else ''}{fmt_short(gan_total)}",
                delta=f"{gan_total/total_in*100:.2f}%" if total_in>0 else '')

        # Chart
        st.divider()
        chart_data = []
        for i, v in enumerate(vueltas):
            _, usdc, ars, gan, p = calc_vuelta(v)
            chart_data.append({'Vuelta':i+1,'Ganancia ARS':gan,'%':p})
        df = pd.DataFrame(chart_data)
        fig = px.bar(df, x='Vuelta', y='Ganancia ARS', text='%',
            labels={'Ganancia ARS':'Ganancia (ARS)','Vuelta':'Vuelta #'},
            color=['#29e8a0' if x>=0 else '#f2566b' for x in df['Ganancia ARS']],
            color_discrete_map="identity")
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Table
        st.divider()
        st.markdown("##### Historial")
        table_data = []
        for i, v in enumerate(reversed(vueltas)):
            usd, usdc, ars, gan, p = calc_vuelta(v)
            is_best = (len(vueltas)-1-i) == best_idx
            best_star = " ⭐" if is_best else ""
            table_data.append({
                '#': f"{len(vueltas)-i}",
                'Fecha': v['fecha'],
                'Inv. (ARS)': f"${v['pesosInicial']:,.0f}",
                'USD': f"{usd:.2f}",
                'USDC': f"{usdc:.2f}",
                'ARS Rec.': f"${ars:,.0f}",
                '%': f"{p:.2f}%{' ⭐' if is_best else ''}",
                'Gan.': f"{'$'+f'{gan:,.0f}' if gan>=0 else '-$'+f'{abs(gan):,.0f}'}",
                'Exchange': v.get('exchange','')
            })
        df2 = pd.DataFrame(table_data)
        st.dataframe(df2, use_container_width=True, hide_index=True)

        # Exports
        c1,c2 = st.columns(2)
        with c1:
            csv_data = "Fecha,PesosInicial,CotizacionCompra,TasaConversion,Comision,PrecioVenta,Exchange\n"
            for v in vueltas:
                csv_data += f"{v['fecha']},{v['pesosInicial']},{v['cotizacionCompra']},{v['tasaConversion']},{v['comisionPct']},{v['precioVenta']},{v.get('exchange','')}\n"
            st.download_button("📥 Exportar CSV", data=csv_data, file_name="mis-vueltas.csv", mime="text/csv", use_container_width=True)
        with c2:
            json_str = json.dumps(vueltas, indent=2, ensure_ascii=False)
            st.download_button("📥 Exportar JSON", data=json_str, file_name="mis-vueltas.json", mime="application/json", use_container_width=True)

        st.divider()
        st.markdown("##### Eliminar vuelta")
        del_id = st.selectbox("Seleccionar vuelta a eliminar",
            options=[(i, f"#{i+1} - {v['fecha']} ${v['pesosInicial']:,.0f}") for i,v in enumerate(vueltas)],
            format_func=lambda x: x[1])
        if st.button("🗑 Eliminar", use_container_width=True):
            idx = del_id[0]
            st.session_state.vueltas.pop(idx)
            save_json(VUELTAS_FILE, st.session_state.vueltas)
            st.rerun()

    vueltas = st.session_state.vueltas
    if not vueltas:
        st.info("Todavía no registraste ninguna vuelta. Agregá la primera con el botón de arriba.")
    else:
        # Stats
        pcts = []
        total_in = 0
        total_out = 0
        for v in vueltas:
            _, _, ars, gan, p = calc_vuelta(v)
            pcts.append(p)
            total_in += v['pesosInicial']
            total_out += ars

        k1,k2,k3,k4 = st.columns(4)
        with k1: st.metric("Vueltas", str(len(vueltas)))
        with k2: st.metric("Promedio %", f"{np.mean(pcts):.3f}%" if pcts else '—')
        with k3: st.metric("Total invertido", fmt_short(total_in))
        with k4:
            gan_total = total_out - total_in
            st.metric("Ganancia total", f"{'+' if gan_total>=0 else ''}{fmt_short(gan_total)}",
                delta=f"{gan_total/total_in*100:.2f}%" if total_in>0 else '')

        # Chart
        st.divider()
        chart_data = []
        for i, v in enumerate(vueltas):
            _, usdc, ars, gan, p = calc_vuelta(v)
            chart_data.append({'Vuelta':i+1,'Ganancia ARS':gan,'%':p})
        df = pd.DataFrame(chart_data)
        fig = px.bar(df, x='Vuelta', y='Ganancia ARS', text='%',
            labels={'Ganancia ARS':'Ganancia (ARS)','Vuelta':'Vuelta #'},
            color=['#29e8a0' if x>=0 else '#f2566b' for x in df['Ganancia ARS']],
            color_discrete_map="identity")
        fig.update_traces(texttemplate='%{text:.2f}%', textposition='outside')
        fig.update_layout(height=300, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True)

        # Table
        st.divider()
        st.markdown("##### Historial")
        table_data = []
        for v in reversed(vueltas):
            usd, usdc, ars, gan, p = calc_vuelta(v)
            table_data.append({
                'Fecha': v['fecha'],
                'Inv.': f"${v['pesosInicial']:,.0f}",
                'USD': f"{usd:.2f}",
                'USDC': f"{usdc:.2f}",
                'ARS': f"${ars:,.0f}",
                '%': f"{p:.2f}%",
                'Gan.': f"{'$'+f'{gan:,.0f}' if gan>=0 else '-$'+f'{abs(gan):,.0f}'}",
                'Ex.': v.get('exchange','')
            })
        df2 = pd.DataFrame(table_data)
        st.dataframe(df2, use_container_width=True, hide_index=True)

        # Exports
        c1,c2 = st.columns(2)
        with c1:
            csv_data = "Fecha,PesosInicial,CotizacionCompra,TasaConversion,Comision,PrecioVenta,Exchange\n"
            for v in vueltas:
                csv_data += f"{v['fecha']},{v['pesosInicial']},{v['cotizacionCompra']},{v['tasaConversion']},{v['comisionPct']},{v['precioVenta']},{v.get('exchange','')}\n"
            st.download_button("📥 Exportar CSV", data=csv_data, file_name="mis-vueltas.csv", mime="text/csv", use_container_width=True)
        with c2:
            json_str = json.dumps(vueltas, indent=2, ensure_ascii=False)
            st.download_button("📥 Exportar JSON", data=json_str, file_name="mis-vueltas.json", mime="application/json", use_container_width=True)

        st.divider()
        st.markdown("##### Eliminar vuelta")
        del_id = st.selectbox("Seleccionar vuelta a eliminar",
            options=[(i, f"#{i+1} - {v['fecha']} ${v['pesosInicial']:,.0f}") for i,v in enumerate(vueltas)],
            format_func=lambda x: x[1])
        if st.button("🗑 Eliminar", use_container_width=True):
            idx = del_id[0]
            st.session_state.vueltas.pop(idx)
            save_json(VUELTAS_FILE, st.session_state.vueltas)
            st.rerun()

# ════════════════════════════════════════
# TAB 2: ALERTAS
# ════════════════════════════════════════
with tabs[2]:
    st.markdown("### 🔔 Alertas de precio")
    st.info("Las alertas verifican cotizaciones cada 60 segundos contra las APIs.")

    prices = {}
    if o_venta: prices['dolar_oficial'] = o_venta
    if blue_compra: prices['dolar_blue'] = blue_compra
    if mep_compra: prices['dolar_mep'] = mep_compra
    if ccl_compra: prices['dolar_ccl'] = ccl_compra
    if best_usdt_sell: prices['usdt_ars'] = best_usdt_sell['bid']
    if best_usdc_sell: prices['usdc_ars'] = best_usdc_sell['bid']

    # Add new alert
    with st.form("alert_form"):
        c1,c2 = st.columns(2)
        with c1:
            alert_type = st.selectbox("Tipo", list(prices.keys()) if prices else ['dolar_oficial'])
            alert_name = {
                'dolar_oficial':'🇺🇸 Dólar Oficial','dolar_blue':'🇺🇸 Blue','dolar_mep':'📈 MEP',
                'dolar_ccl':'🌎 CCL','usdt_ars':'USDT/ARS','usdc_ars':'USDC/ARS'
            }.get(alert_type, alert_type)
        with c2:
            condition = st.selectbox("Condición", ["mayor a","menor a"])
            alert_price = st.number_input("Precio", value=float(prices.get(alert_type,1500)), step=100.0, format="%.2f")
        if st.form_submit_button("➕ Crear alerta"):
            current = prices.get(alert_type,0)
            triggered = (condition=="mayor a" and current>alert_price) or (condition=="menor a" and current<alert_price and current>0)
            st.session_state.alerts.append({
                'id':str(uuid.uuid4())[:8],
                'type':alert_type,
                'name':alert_name,
                'condition':condition,
                'price':alert_price,
                'triggered':triggered,
                'created':datetime.now().isoformat()
            })
            save_json(ALERTS_FILE, st.session_state.alerts)
            st.rerun()

    if not st.session_state.alerts:
        st.caption("No hay alertas creadas.")
    else:
        for a in st.session_state.alerts:
            current = prices.get(a['type'],0)
            triggered = (a['condition']=="mayor a" and current>a['price']) or (a['condition']=="menor a" and current<a['price'] and current>0)
            a['triggered'] = triggered
            save_json(ALERTS_FILE, st.session_state.alerts)

            c1,c2,c3 = st.columns([2,2,1])
            with c1:
                status = "🔔" if triggered else "🔕"
                st.markdown(f"{status} **{a['name']}**")
            with c2:
                st.markdown(f"Actual: {fmt(current)} — Alerta: {a['condition']} {fmt(a['price'])}")
            with c3:
                if st.button("🗑", key=f"del_alert_{a['id']}"):
                    st.session_state.alerts = [x for x in st.session_state.alerts if x['id']!=a['id']]
                    save_json(ALERTS_FILE, st.session_state.alerts)
                    st.rerun()
            st.divider()

# ── Footer ──
st.markdown("---")
st.caption("CambioAR · Datos de DolarApi, ComparaDolar y CriptoYa · Actualización cada 2-5 min")
