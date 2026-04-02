import streamlit as st
import pandas as pd
import io

# ---------------------------
# Funzioni helper
# ---------------------------

def safe_str(value):
    if pd.isna(value):
        return ""
    return str(value).strip()

def safe_float(value):
    s = safe_str(value)
    if s == "":
        return 0.0
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0

# Funzione per pulire tutto il DataFrame
def clean_dataframe(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))
    return df

# Funzione per l'elaborazione delle righe delle spedizioni
def process_shipping_rows(rows, countrycode_dict):
    adjusted_rows = rows.copy()
    errors = []

    for index, row in adjusted_rows.iterrows():
        nazione = safe_str(row.get('NAZIONE', ''))

        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            try:
                costo_spedizione = safe_float(row.get('COSTI_SPEDIZIONE', ''))
                costo_senza_iva = costo_spedizione / (1 + iva / 100)
                formatted_price = round(costo_senza_iva, 2)
                adjusted_rows.at[index, 'PREZZO_1'] = formatted_price
            except Exception as e:
                errors.append(
                    f"Errore nella riga {index + 1}: {safe_str(row.get('COSTI_SPEDIZIONE', ''))} - {e}"
                )
        else:
            adjusted_rows.at[index, 'PREZZO_1'] = safe_float(row.get('COSTI_SPEDIZIONE', ''))

    for error in errors:
        st.error(error)

    adjusted_rows['COD_ART'] = adjusted_rows['COSTI_SPEDIZIONE'].apply(
        lambda x: f"SHIPPINGCOSTS{safe_str(x)}"
    )
    adjusted_rows['COD_ART_DOC'] = adjusted_rows['COD_ART']
    adjusted_rows['DESCR_ART'] = "Shipping Costs"
    adjusted_rows['DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows['DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows['PROGRESSIVO_RIGA'] = adjusted_rows['PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows['HSCODE'] = ""

    return adjusted_rows

# Funzione per l'elaborazione delle righe dell'IVA
def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()

    vat_rows = vat_rows[vat_rows['NAZIONE'].astype(str) != "86"]
    vat_rows = vat_rows[vat_rows['NAZIONE'].isin(countrycode_dict.keys())]

    for index, row in vat_rows.iterrows():
        num_doc = safe_str(row.get('NUM_DOC', ''))
        sezionale = safe_str(row.get('SEZIONALE', ''))
        iva = countrycode_dict.get(safe_str(row.get('NAZIONE', '')), 0)

        if not isinstance(iva, (int, float)):
            st.error(f"IVA non valida per la nazione {safe_str(row.get('NAZIONE', ''))}: {iva}")
            continue

        related_rows = df_original[
            (df_original['NUM_DOC'].astype(str) == num_doc) &
            (df_original['SEZIONALE'].astype(str) == sezionale)
        ]
        related_rows_unique = related_rows.drop_duplicates(subset=['PROGRESSIVO_RIGA'])

        try:
            sum_prezzo = related_rows_unique['PREZZO_1'].apply(safe_float).sum()
        except Exception as e:
            st.error(
                f"Errore nella conversione o nella somma di PREZZO_1 "
                f"per NUM_DOC {num_doc} e SEZIONALE {sezionale}: {e}"
            )
            continue

        costo_iva = sum_prezzo * iva / 100
        formatted_vat = round(costo_iva, 2)
        vat_rows.at[index, 'PREZZO_1'] = formatted_vat

    vat_rows['COD_ART'] = "VAT"
    vat_rows['COD_ART_DOC'] = vat_rows['COD_ART']
    vat_rows['DESCR_ART'] = "VAT"
    vat_rows['DESCR_ART_ESTESA'] = "VAT"
    vat_rows['DESCRIZIONE_RIGA'] = "VAT"
    vat_rows['PROGRESSIVO_RIGA'] = vat_rows['PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows['HSCODE'] = ""

    return vat_rows

# Funzione per la rimozione dei valori in COD_FISCALE basati su no_cod_fiscale.txt
def remove_cod_fiscale(df, no_cod_fiscale_list):
    for index, row in df.iterrows():
        cod_fiscale = row.get('COD_FISCALE', '')
        if pd.isna(cod_fiscale):
            continue
        cod_fiscale = safe_str(cod_fiscale).upper()
        if cod_fiscale in no_cod_fiscale_list:
            df.at[index, 'COD_FISCALE'] = ""
        else:
            df.at[index, 'COD_FISCALE'] = cod_fiscale
    return df

# ---------------------------
# App Streamlit
# ---------------------------

st.title('Modifica File CSV per Costi di Spedizione e IVA')

uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    try:
        # Legge tutto come stringa per evitare dtype ballerini
        df = pd.read_csv(
            uploaded_file,
            delimiter=';',
            dtype=str,
            keep_default_na=False,
            encoding='utf-8'
        )
        df = clean_dataframe(df)
    except Exception as e:
        st.error(f"Errore nella lettura del CSV: {e}")
        st.stop()

    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None, dtype=str)
        countrycode_df = clean_dataframe(countrycode_df)
        countrycode_df[2] = countrycode_df[2].apply(safe_float)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    try:
        with open('no_cod_fiscale.txt', 'r', encoding='utf-8') as f:
            no_cod_fiscale_content = f.read().strip()
            no_cod_fiscale_list = [x.strip().upper() for x in no_cod_fiscale_content.split(';')]
    except Exception as e:
        st.error(f"Errore nella lettura di no_cod_fiscale.txt: {e}")
        no_cod_fiscale_list = []

    all_rags = list(df['RAG_SOCIALE'].dropna().unique())
    name_mapping = {safe_str(rag).upper(): rag for rag in all_rags if safe_str(rag) != ""}
    sorted_keys = sorted(name_mapping.keys())

    selected_rags_upper = [key for key in sorted_keys if st.checkbox(key, key=key)]

    if selected_rags_upper:
        selected_rags = [name_mapping[rag] for rag in selected_rags_upper]
        df = df[df['RAG_SOCIALE'].isin(selected_rags)]
    else:
        st.write("Nessuna selezione effettuata, visualizzati tutti i dati.")

    # Tiene solo le righe con costo spedizione > 0
    costs_rows = df[df['COSTI_SPEDIZIONE'].apply(safe_float) != 0]
    unique_costs_rows = costs_rows.drop_duplicates(subset=['NUM_DOC'])

    adjusted_rows = process_shipping_rows(unique_costs_rows, countrycode_dict)
    df_with_shipping = pd.concat([df, adjusted_rows], ignore_index=True)

    vat_rows = process_vat_rows(unique_costs_rows, countrycode_dict, df_with_shipping)
    final_df = pd.concat([df_with_shipping, vat_rows], ignore_index=True)

    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0']
    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0,00']
    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0.00']

    for index, row in final_df.iterrows():
        partita_iva_is_empty = safe_str(row.get('PARTITA_IVA', '')) == ""
        nazione = safe_str(row.get('NAZIONE', ''))

        if nazione in countrycode_dict and partita_iva_is_empty:
            iva_to_remove = countrycode_dict[nazione]
            try:
                prezzo_con_iva = safe_float(row.get('PREZZO_1', ''))
                prezzo_senza_iva = prezzo_con_iva / (1 + iva_to_remove / 100)
                final_df.at[index, 'PREZZO_1'] = round(prezzo_senza_iva, 2)
            except Exception as e:
                st.error(f"Errore nella rimozione dell'IVA da PREZZO_1 per la riga {index}: {e}")

    final_df.sort_values(by=['NUM_DOC', 'PROGRESSIVO_RIGA'], inplace=True)

    new_progressivo = (final_df.groupby(['NUM_DOC', 'PROGRESSIVO_RIGA']).ngroup() + 1)
    final_df['PROGRESSIVO_RIGA'] = new_progressivo

    final_df = remove_cod_fiscale(final_df, no_cod_fiscale_list)

    # Se ALI_IVA è stringa, confronta con "47"
    final_df = final_df[~((final_df['ALI_IVA'].astype(str) == "47") & (final_df['COD_ART'] == "VAT"))]

    csv = final_df.to_csv(
        sep=';',
        index=False,
        float_format='%.2f'
    ).encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    st.write("Anteprima dei dati filtrati:", final_df)

    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
