import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    # Lettura del file caricato con sostituzione della virgola con il punto nei numeri
    df = pd.read_csv(uploaded_file, delimiter=';')
    df[' PREZZO_1'] = df[' PREZZO_1'].str.replace(',', '.').astype(float)
    df[' COSTI_SPEDIZIONE'] = df[' COSTI_SPEDIZIONE'].str.replace(',', '.').astype(float)

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
    final_df = pd.concat([df, vat_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)

    # Converti i numeri in stringhe con virgole per i decimali prima di esportare
    final_df[' PREZZO_1'] = final_df[' PREZZO_1'].apply(lambda x: '{:.2f}'.format(x).replace('.', ','))
    final_df[' COSTI_SPEDIZIONE'] = final_df[' COSTI_SPEDIZIONE'].apply(lambda x: '{:.2f}'.format(x).replace('.', ','))

    # Converti il dataframe finale in CSV
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv.encode('utf-8')),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )

    st.balloons()
