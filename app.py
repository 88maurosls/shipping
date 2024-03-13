import streamlit as st
import pandas as pd
import io

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione')

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

    # Apporta le modifiche necessarie
    adjusted_rows = unique_costs_rows.copy()
    for index, row in adjusted_rows.iterrows():
    nazione = row[' NAZIONE'].strip()  # Rimuove gli spazi bianchi prima e dopo il testo
    if nazione in countrycode_dict:
        iva = countrycode_dict[nazione]
        costo_spedizione = row[' COSTI_SPEDIZIONE']
        costo_senza_iva = costo_spedizione - (costo_spedizione * iva / 100)
        # Formatta il costo senza IVA con due cifre decimali
        adjusted_rows.at[index, ' PREZZO_1'] = "{:.2f}".format(costo_senza_iva)
    else:
        # Se la nazione non è nel dizionario, mantenere il valore originale di COSTI_SPEDIZIONE
        # Converti a stringa per mantenere consistenza nel formato del CSV
        adjusted_rows.at[index, ' PREZZO_1'] = "{:.2f}".format(row[' COSTI_SPEDIZIONE'])


    adjusted_rows[' COD_ART'] = adjusted_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    adjusted_rows[' COD_ART_DOC'] = adjusted_rows[' COD_ART']
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

    # Aggiungi le righe modificate al dataframe originale
    final_df = pd.concat([df, adjusted_rows], ignore_index=True)

    # Ordina il dataframe finale per NUM_DOC
    final_df.sort_values(by=[' NUM_DOC'], inplace=True)

    # Converti il dataframe finale in CSV
    csv = final_df.to_csv(sep=';', index=False).encode('utf-8')

    # Bottone per il download del file modificato
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
    st.balloons()
