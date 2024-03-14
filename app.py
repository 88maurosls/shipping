import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato
    df = pd.read_csv(uploaded_file, delimiter=';')

    # Leggi il file countrycode.txt e crea un dizionario
    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]

    # Filtra le righe uniche basate su NUM_DOC
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC'])

    # Apporta le modifiche necessarie per le righe degli Shipping Costs
    adjusted_rows = unique_costs_rows.copy()
    for index, row in adjusted_rows.iterrows():
        nazione = row[' NAZIONE']
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            costo_spedizione = row[' COSTI_SPEDIZIONE']
            costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
            formatted_price = int(costo_senza_iva) if costo_senza_iva == int(costo_senza_iva) else costo_senza_iva
            adjusted_rows.at[index, ' PREZZO_1'] = formatted_price
        else:
            adjusted_rows.at[index, ' PREZZO_1'] = row[' COSTI_SPEDIZIONE']

    adjusted_rows[' COD_ART'] = adjusted_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    adjusted_rows[' COD_ART_DOC'] = adjusted_rows[' COD_ART']
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Calcolare il totale dei prezzi dei prodotti per ogni NUM_DOC
    total_product_price = df.groupby(' NUM_DOC')[' PREZZO_1'].sum()

    # Crea una seconda riga aggiuntiva per l'IVA solo per le nazioni presenti in countrycode.txt
    vat_rows = unique_costs_rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]

    # Calcolare l'IVA per ogni NUM_DOC
    for num_doc in unique_costs_rows[' NUM_DOC'].unique():
        total_price = total_product_price[num_doc]
        shipping_cost = unique_costs_rows.loc[unique_costs_rows[' NUM_DOC'] == num_doc, ' COSTI_SPEDIZIONE'].iloc[0]
        total_price += shipping_cost
        country = unique_costs_rows.loc[unique_costs_rows[' NUM_DOC'] == num_doc, ' NAZIONE'].iloc[0]
        iva_percentage = countrycode_dict.get(country, 0)
        iva_amount = total_price * iva_percentage / 100
        vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' PREZZO_1'] = iva_amount

    vat_rows[' COD_ART'] = "VAT"
    vat_rows[' COD_ART_DOC'] = vat_rows[' COD_ART']
    vat_rows[' DESCR_ART'] = "VAT"
    vat_rows[' DESCR_ART_ESTESA'] = "VAT"
    vat_rows[' DESCRIZIONE_RIGA'] = "VAT"
    vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Aggiungi sia le righe degli Shipping Costs che le righe dell'IVA al dataframe originale
    final_df = pd.concat([df, adjusted_rows, vat_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)

    # Converti il dataframe finale in CSV
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )

    st.balloons()
