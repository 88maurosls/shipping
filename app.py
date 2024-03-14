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
            # Se la nazione non è nel dizionario, mantenere il valore originale di COSTI_SPEDIZIONE
            adjusted_rows.at[index, ' PREZZO_1'] = row[' COSTI_SPEDIZIONE']

    adjusted_rows[' COD_ART'] = adjusted_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    adjusted_rows[' COD_ART_DOC'] = adjusted_rows[' COD_ART']
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Crea una seconda riga aggiuntiva per l'IVA solo per le nazioni presenti in countrycode.txt
    vat_rows = unique_costs_rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]  # Filtra solo le nazioni presenti nel dizionario

    # Inizializza un dizionario per tenere traccia dei totali per ogni 'NUM_DOC'
    num_doc_totals = {}

    for index, row in vat_rows.iterrows():
        num_doc = row[' NUM_DOC']
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        
        # Calcola l'IVA
        iva = countrycode_dict[row[' NAZIONE']]
        costo_iva = costo_spedizione * iva / 100
        
        # Calcola la somma di 'PREZZO_1' per lo stesso 'NUM_DOC' ma con 'PROGRESSIVO_RIGA' differente
        if num_doc in num_doc_totals:
            num_doc_totals[num_doc] += costo_spedizione
        else:
            num_doc_totals[num_doc] = costo_spedizione
        
    # Aggiungi 'PREZZO_1' come totale per ogni 'NUM_DOC' nel dataframe dell'IVA
    vat_rows[' PREZZO_1'] = vat_rows[' NUM_DOC'].map(num_doc_totals)
    
    # Rimuovi righe duplicati e aggiungi 'PROGRESSIVO_RIGA' corretto
    vat_rows = vat_rows.drop_duplicates(subset=[' NUM_DOC'])
    vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"

    # Calcola e aggiungi l'IVA alla riga dell'IVA stessa
    vat_rows['IVA'] = vat_rows[' PREZZO_1'] * vat_rows['IVA'] / 100

    # Converti il dataframe finale in CSV
    final_df = pd.concat([df, adjusted_rows, vat_rows], ignore_index=True)
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
    st.balloons()
