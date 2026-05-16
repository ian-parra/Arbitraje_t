CREATE TABLE vueltas (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  fecha TEXT NOT NULL,
  "pesosInicial" DOUBLE PRECISION NOT NULL,
  "cotizacionCompra" DOUBLE PRECISION NOT NULL,
  "tasaConversion" DOUBLE PRECISION NOT NULL,
  "comisionPct" DOUBLE PRECISION NOT NULL,
  "precioVenta" DOUBLE PRECISION NOT NULL,
  exchange TEXT DEFAULT '',
  notas TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE alerts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  type TEXT NOT NULL,
  name TEXT NOT NULL,
  condition TEXT NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  is_route BOOLEAN DEFAULT FALSE,
  triggered BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE vueltas ENABLE ROW LEVEL SECURITY;
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users own their vueltas"
  ON vueltas FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users own their alerts"
  ON alerts FOR ALL
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);
