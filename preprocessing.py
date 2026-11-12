from pathlib import Path
import pandas as pd

COLS_TO_KEEP = [
    "id_mutation",
    "date_mutation",
    "nature_mutation",
    "valeur_fonciere",
    "code_departement",
    "code_commune",
    "code_postal",
    "nom_commune",
    "nombre_lots",
    "type_local",
    "surface_reelle_bati",
    "nombre_pieces_principales",
    "surface_terrain",
    "longitude",
    "latitude",
]

# 2. Percorso della cartella principale
base_dir = Path("data/dvf")

# Cerca tutti i file .csv.gz dentro le sottocartelle (es. data/dvf/2021/*.csv.gz)
gz_files = sorted(list(base_dir.rglob("*.csv.gz")))

print(f"Trovati {len(gz_files)} file da elaborare:")
for f in gz_files:
    print(f" - {f}")

dataframes = []

# 3. Iterazione sui file delle 5 cartelle
for file_path in gz_files:
    print(f"\nElaborazione in corso: {file_path}...")

    chunks = []
    # Lettura a blocchi da 100.000 righe alla volta per ottimizzare la memoria
    for chunk in pd.read_csv(
        file_path,
        compression="gzip",
        usecols=COLS_TO_KEEP,
        low_memory=False,
        chunksize=100_000,
    ):
        # Filtro 1: Solo compravendite residenziali (Maison / Appartement) con valori > 0
        filtered_chunk = chunk[
            (chunk["nature_mutation"] == "Vente")
            & (chunk["type_local"].isin(["Maison", "Appartement"]))
            & (chunk["valeur_fonciere"] > 0)
            & (chunk["surface_reelle_bati"] > 0)
        ].copy()

        # Filtro 2: Rimuovi le righe prive di coordinate geografiche
        filtered_chunk = filtered_chunk.dropna(
            subset=["longitude", "latitude"]
        )

        chunks.append(filtered_chunk)

    # Concatena i blocchi dell'anno corrente
    df_year = pd.concat(chunks, ignore_index=True)
    dataframes.append(df_year)
    print(f"  -> Estratte {len(df_year):,} transazioni residenziali valide.")

# 4. Unione di tutte le annate (2021-2025)
df_all = pd.concat(dataframes, ignore_index=True)

# Sostituisci i valori NaN della superficie terreno con 0 (es. per gli appartamenti)
df_all["surface_terrain"] = df_all["surface_terrain"].fillna(0)

# Pulizia tipo dato: assicuriamoci che le date siano in formato datetime
df_all["date_mutation"] = pd.to_datetime(df_all["date_mutation"])

print("\n================ RIEPILOGO ================")
print(f"Totale transazioni estratte (2021-2025): {len(df_all):,}")
print(f"Uso memoria RAM: {df_all.memory_usage().sum() / 1e6:.2f} MB")

# Converti esplicitamente in stringa tutte le colonne alfanumeriche/geografiche
str_columns = [
    "id_mutation",
    "code_departement",
    "code_commune",
    "code_postal",
]

for col in str_columns:
    if col in df_all.columns:
        df_all[col] = df_all[col].astype(str)

# 5. Salvataggio in un unico file Parquet
output_parquet = base_dir / "dvf_2021_2025.parquet"
df_all.to_parquet(output_parquet, index=False)

print(f"\nDataset unico salvato con successo in: {output_parquet}")