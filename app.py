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

def format_number(value, decimals=2):
    s = safe_str(value)
    if s == "":
        return ""
    val = safe_float(value)
    return f"{val:.{decimals}f}".replace(".", ",")

def clean_dataframe(df):
    df = df.copy()
    df.columns = df.columns.str.strip()
    df = df.apply(lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x))
    return df

# ---------------------------
# Funzione per l'elaborazione delle righe delle spedizioni
# ---------------------------

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
                adjusted_rows.at[index, 'PREZZO_1'] = format_number(costo_senza_iva, 2)
            except Exception as e:
                errors.append(
                    f"Errore nella riga {index + 1}: {safe_str(row.get('COSTI_SPEDIZIONE', ''))} - {e}"
                )
        else:
            adjusted_rows.at[index, 'PREZZO_1'] = format_number(
                safe_float(row.get('COSTI_SPEDIZIONE', '')), 2
            )

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

# ---------------------------
# Funzione per l'elaborazione delle righe dell'IVA
# ---------------------------

def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()

    vat_rows = vat_rows[vat_rows['NAZIONE'].astype(str) != "86"]
    vat_rows = vat_rows[vat_rows['NAZIONE'].astype(str).isin(countrycode_dict.keys())]

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
        ].copy()

        # Evita righe VAT già eventualmente presenti
        related_rows = related_rows[related_rows['COD_ART'].astype(str) != 'VAT']

        # Somma una sola volta ogni progressivo
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
        vat_rows.at[index, 'PREZZO_1'] = format_number(costo_iva, 2)

    vat_rows['COD_ART'] = "VAT"
    vat_rows['COD_ART_DOC'] = vat_rows['COD_ART']
    vat_rows['DESCR_ART'] = "VAT"
    vat_rows['DESCR_ART_ESTESA'] = "VAT"
    vat_rows['DESCRIZIONE_RIGA'] = "VAT"
    vat_rows['PROGRESSIVO_RIGA'] = vat_rows['PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows['HSCODE'] = ""

    return vat_rows

# ---------------------------
# Funzione per la rimozione dei valori in COD_FISCALE
# ---------------------------

def remove_cod_fiscale(df, no_cod_fiscale_list):
    df = df.copy()

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
# Formattazione finale colonne
# ---------------------------

def format_output_columns(final_df):
    final_df = final_df.copy()

    if 'PREZZO_1' in final_df.columns:
        def format_prezzo_row(row):
            cod_art = safe_str(row.get('COD_ART', ''))
            descr_art = safe_str(row.get('DESCR_ART', ''))

            if cod_art == 'VAT' or descr_art == 'Shipping Costs':
                return format_number(row.get('PREZZO_1', ''), 2)

            return safe_str(row.get('PREZZO_1', ''))

        final_df['PREZZO_1'] = final_df.apply(format_prezzo_row, axis=1)

    if 'COSTI_SPEDIZIONE' in final_df.columns:
        final_df['COSTI_SPEDIZIONE'] = final_df['COSTI_SPEDIZIONE'].apply(
            lambda x: "" if safe_str(x) == "" else format_number(x, 2)
        )

    if 'EXSTRASCONTO' in final_df.columns:
        final_df['EXSTRASCONTO'] = final_df['EXSTRASCONTO'].apply(
            lambda x: "" if safe_str(x) == "" else format_number(x, 2)
        )

    return final_df

# ---------------------------
# App Streamlit
# ---------------------------

st.title('Modifica File CSV per Costi di Spedizione e IVA')

uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    try:
        df = pd.read_csv(
            uploaded_file,
            delimiter=';',
            dtype=str,
            keep_default_na=False,
            encoding='utf-8'
        )
        df = clean_dataframe(df)
        df['_ORIG_ROW_ORDER'] = range(len(df))
    except Exception as e:
        st.error(f"Errore nella lettura del CSV: {e}")
        st.stop()

    try:
        countrycode_df = pd.read_csv(
            'countrycode.txt',
            delimiter=';',
            header=None,
            dtype=str,
            keep_default_na=False
        )

        countrycode_df = countrycode_df.apply(
            lambda col: col.map(lambda x: x.strip() if isinstance(x, str) else x)
        )

        countrycode_dict = dict(
            zip(
                countrycode_df.iloc[:, 0].astype(str).str.strip(),
                countrycode_df.iloc[:, 2].astype(str).str.strip().str.replace(',', '.', regex=False).astype(float)
            )
        )

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
        df = df[df['RAG_SOCIALE'].isin(selected_rags)].copy()
    else:
        st.write("Nessuna selezione effettuata, visualizzati tutti i dati.")

    # ---------------------------------------------------
    # SHIPPING:
    # solo per documenti con COSTI_SPEDIZIONE != 0
    # ---------------------------------------------------
    shipping_base_rows = df[df['COSTI_SPEDIZIONE'].apply(safe_float) != 0].copy()
    shipping_base_rows = shipping_base_rows.drop_duplicates(subset=['NUM_DOC', 'SEZIONALE'])

    adjusted_rows = process_shipping_rows(shipping_base_rows, countrycode_dict)
    adjusted_rows['_ORIG_ROW_ORDER'] = pd.NA

    df_with_shipping = pd.concat([df, adjusted_rows], ignore_index=True)

    # ---------------------------------------------------
    # VAT:
    # per tutti i documenti esteri validi, anche se spedizione = 0
    # ---------------------------------------------------
    vat_base_rows = df.drop_duplicates(subset=['NUM_DOC', 'SEZIONALE']).copy()
    vat_rows = process_vat_rows(vat_base_rows, countrycode_dict, df_with_shipping)
    vat_rows['_ORIG_ROW_ORDER'] = pd.NA

    final_df = pd.concat([df_with_shipping, vat_rows], ignore_index=True)

    # Rimuovi eventuali shipping a zero
    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0']
    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0,00']
    final_df = final_df[final_df['COD_ART'] != 'SHIPPINGCOSTS0.00']

    # ---------------------------------------------------
    # Rimozione IVA da PREZZO_1 dove richiesto
    # ma NON toccare la riga VAT
    # ---------------------------------------------------
    for index, row in final_df.iterrows():
        partita_iva_is_empty = safe_str(row.get('PARTITA_IVA', '')) == ""
        nazione = safe_str(row.get('NAZIONE', ''))
        cod_art = safe_str(row.get('COD_ART', ''))
        descr_art = safe_str(row.get('DESCR_ART', ''))

        if nazione in countrycode_dict and partita_iva_is_empty:
            if cod_art == "VAT":
                continue

            iva_to_remove = countrycode_dict[nazione]

            try:
                prezzo_con_iva = safe_float(row.get('PREZZO_1', ''))
                prezzo_senza_iva = prezzo_con_iva / (1 + iva_to_remove / 100)

                is_shipping = descr_art == 'Shipping Costs'

                final_df.at[index, 'PREZZO_1'] = format_number(
                    prezzo_senza_iva,
                    2 if is_shipping else 3
                )

            except Exception as e:
                st.error(f"Errore nella rimozione dell'IVA da PREZZO_1 per la riga {index}: {e}")

    final_df = remove_cod_fiscale(final_df, no_cod_fiscale_list)

    final_df = final_df[
        ~((final_df['ALI_IVA'].astype(str) == "47") & (final_df['COD_ART'] == "VAT"))
    ]

    # ---------------------------------------------------
    # Ordinamento finale corretto:
    # prodotti originali prima,
    # SHIPPING penultima,
    # VAT ultima
    # ---------------------------------------------------
    def row_group_type(row):
        cod_art = safe_str(row.get('COD_ART', ''))
        descr_art = safe_str(row.get('DESCR_ART', ''))

        if cod_art == "VAT":
            return "VAT"
        if descr_art == "Shipping Costs":
            return "SHIPPING"
        return "PRODUCT"

    final_df['_ROW_GROUP_TYPE'] = final_df.apply(row_group_type, axis=1)

    doc_max_order = (
        final_df[final_df['_ROW_GROUP_TYPE'] == 'PRODUCT']
        .groupby(['NUM_DOC', 'SEZIONALE'])['_ORIG_ROW_ORDER']
        .max()
        .reset_index()
        .rename(columns={'_ORIG_ROW_ORDER': '_DOC_MAX_ORDER'})
    )

    final_df = final_df.merge(doc_max_order, on=['NUM_DOC', 'SEZIONALE'], how='left')
    final_df['_DOC_MAX_ORDER'] = final_df['_DOC_MAX_ORDER'].fillna(0)

    def final_sort_order(row):
        row_type = row['_ROW_GROUP_TYPE']

        if row_type == 'PRODUCT':
            return row['_ORIG_ROW_ORDER']
        if row_type == 'SHIPPING':
            return row['_DOC_MAX_ORDER'] + 1
        if row_type == 'VAT':
            return row['_DOC_MAX_ORDER'] + 2
        return row['_DOC_MAX_ORDER'] + 99

    final_df['_FINAL_SORT_ORDER'] = final_df.apply(final_sort_order, axis=1)

    final_df.sort_values(
        by=['NUM_DOC', 'SEZIONALE', '_FINAL_SORT_ORDER'],
        inplace=True,
        kind='stable'
    )

    final_df['PROGRESSIVO_RIGA'] = final_df.groupby(['NUM_DOC', 'SEZIONALE']).cumcount() + 1

    final_df.drop(
        columns=['_ROW_GROUP_TYPE', '_DOC_MAX_ORDER', '_FINAL_SORT_ORDER'],
        inplace=True
    )

    final_df = format_output_columns(final_df)

    if '_ORIG_ROW_ORDER' in final_df.columns:
        final_df.drop(columns=['_ORIG_ROW_ORDER'], inplace=True)

    csv = final_df.to_csv(
        sep=';',
        index=False
    ).encode('utf-8')

    st.write("Anteprima dei dati filtrati:", final_df)

    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
