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
    
    # Identifica le righe con COSTI_SPEDIZIONE diversi da 0
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]
    
    # Filtra le righe uniche basate su NUM_DOC e PROGRESSIVO_RIGA per evitare duplicati
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC', ' PROGRESSIVO_RIGA'])
    
    # Calcolare il totale dei prezzi dei prodotti per ogni NUM_DOC senza duplicati in PROGRESSIVO_RIGA
    total_product_price = df.drop_duplicates(subset=[' NUM_DOC', ' PROGRESSIVO_RIGA']).groupby(' NUM_DOC')[' PREZZO_1'].sum()

    # Crea una seconda riga aggiuntiva per l'IVA solo per le nazioni presenti in countrycode.txt
    vat_rows = unique_costs_rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]
    for num_doc in unique_costs_rows[' NUM_DOC'].unique():
        if unique_costs_rows[unique_costs_rows[' NUM_DOC'] == num_doc][' NAZIONE'].iloc[0] in countrycode_dict:
            iva = countrycode_dict[unique_costs_rows[unique_costs_rows[' NUM_DOC'] == num_doc][' NAZIONE'].iloc[0]]
            total_price = total_product_price[num_doc] + unique_costs_rows[unique_costs_rows[' NUM_DOC'] == num_doc][' COSTI_SPEDIZIONE'].iloc[0]
            costo_iva = (total_price * iva) / 100
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' PREZZO_1'] = costo_iva
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' COD_ART'] = "VAT"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' COD_ART_DOC'] = "VAT"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' DESCR_ART'] = "VAT"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' DESCR_ART_ESTESA'] = "VAT"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' DESCRIZIONE_RIGA'] = "VAT"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' PROGRESSIVO_RIGA'] = unique_costs_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
            vat_rows.loc[vat_rows[' NUM_DOC'] == num_doc, ' HSCODE'] = ""
        else:
            vat_rows = vat_rows[vat_rows[' NUM_DOC'] != num_doc]

    # Unire le righe di costo di spedizione e IVA al dataframe originale
    final_df = pd.concat([df, vat_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC e PROGRESSIVO_RIGA
    final_df.sort_values(by=[' NUM_DOC', ' PROGRESSIVO_RIGA'], inplace=True)

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
