import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato
    df = pd.read_csv(uploaded_file, delimiter=';', decimal=',')

    # Leggi il file countrycode.txt e crea un dizionario
    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None, decimal=',')
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Aggiungi le righe degli Shipping Costs
    shipping_rows = df[df[' COSTI_SPEDIZIONE'] != 0].copy()
    shipping_rows[' PREZZO_1'] = shipping_rows.apply(
        lambda x: x[' COSTI_SPEDIZIONE'] / (1 + countrycode_dict.get(x[' NAZIONE'], 0) / 100) if x[' NAZIONE'] in countrycode_dict else x[' COSTI_SPEDIZIONE'],
        axis=1
    )
    shipping_rows[' COD_ART'] = "SHIPPINGCOSTS"
    shipping_rows[' COD_ART_DOC'] = "SHIPPINGCOSTS"
    shipping_rows[' DESCR_ART'] = "Shipping Costs"
    shipping_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    shipping_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    shipping_rows[' PROGRESSIVO_RIGA'] = shipping_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    shipping_rows[' HSCODE'] = ""

    # Aggiungi le righe dell'IVA
    vat_rows = df[df[' NAZIONE'].isin(countrycode_dict)].copy()
    vat_rows[' PREZZO_1'] = vat_rows.apply(
        lambda x: x[' PREZZO_1'] * (countrycode_dict.get(x[' NAZIONE'], 0) / 100),
        axis=1
    )
    vat_rows[' COD_ART'] = "VAT"
    vat_rows[' COD_ART_DOC'] = "VAT"
    vat_rows[' DESCR_ART'] = "VAT"
    vat_rows[' DESCR_ART_ESTESA'] = "VAT"
    vat_rows[' DESCRIZIONE_RIGA'] = "VAT"
    vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows[' HSCODE'] = ""

    # Unisci i dataframe delle righe degli Shipping Costs, del VAT e il dataframe originale
    final_df = pd.concat([df, shipping_rows, vat_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)

    # Converti il dataframe finale in CSV mantenendo il formato originale per i numeri
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f', decimal=',')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv.encode('utf-8')),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )

    st.balloons()
