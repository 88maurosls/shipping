import streamlit as st
import pandas as pd
import io

# Funzione per l'elaborazione delle righe delle spedizioni
def process_shipping_rows(rows, countrycode_dict):
    adjusted_rows = rows.copy()
    errors = []  # Lista per memorizzare gli errori
    for index, row in adjusted_rows.iterrows():
        nazione = row[' NAZIONE']
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            try:
                # Rimuovi spazi bianchi, sostituisci virgole con punti e converti a float
                costo_spedizione = float(row[' COSTI_SPEDIZIONE'].strip().replace(',', '.'))
                costo_senza_iva = costo_spedizione / (1 + iva / 100)
                formatted_price = round(costo_senza_iva, 2)
                adjusted_rows.at[index, ' PREZZO_1'] = formatted_price
            except ValueError as ve:
                errors.append(f"Valore non valido per COSTI_SPEDIZIONE nella riga {index + 1}: {row[' COSTI_SPEDIZIONE']} - {ve}")
            except Exception as e:
                errors.append(f"Errore nella riga {index + 1}: {e}")
        else:
            adjusted_rows.at[index, ' PREZZO_1'] = row[' COSTI_SPEDIZIONE']

    # Stampa gli errori
    for error in errors:
        st.error(error)

    adjusted_rows[' COD_ART'] = adjusted_rows[' COSTI_SPEDIZIONE'].apply(lambda x: f"SHIPPINGCOSTS{x}")
    adjusted_rows[' COD_ART_DOC'] = adjusted_rows[' COD_ART']
    adjusted_rows[' DESCR_ART'] = "Shipping Costs"
    adjusted_rows[' DESCR_ART_ESTESA'] = "Shipping Costs"
    adjusted_rows[' DESCRIZIONE_RIGA'] = "Shipping Costs"
    adjusted_rows[' PROGRESSIVO_RIGA'] = adjusted_rows[' PROGRESSIVO_RIGA'].astype(str) + "-2"
    adjusted_rows[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE
    return adjusted_rows

# Funzione per l'elaborazione delle righe dell'IVA
def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].astype(str) != "86"]
    vat_rows = vat_rows[vat_rows[' NAZIONE'].isin(countrycode_dict.keys())]

    for index, row in vat_rows.iterrows():
        num_doc = row[' NUM_DOC']
        iva = countrycode_dict.get(row[' NAZIONE'], 0)

        if not isinstance(iva, (int, float)):
            st.error(f"IVA non valida per la nazione {row[' NAZIONE']}: {iva}")
            continue

        related_rows = df_original[df_original[' NUM_DOC'] == num_doc]
        related_rows_unique = related_rows.drop_duplicates(subset=[' PROGRESSIVO_RIGA'])

        try:
            sum_prezzo = related_rows_unique[' PREZZO_1'].astype(str).str.replace(",", ".").astype(float).sum()
        except Exception as e:
            st.error(f"Errore nella conversione o nella somma di 'PREZZO_1' per NUM_DOC {num_doc}: {e}")
            continue

        costo_iva = sum_prezzo * iva / 100
        formatted_vat = round(costo_iva, 2)
        vat_rows.at[index, ' PREZZO_1'] = formatted_vat

    vat_rows[' COD_ART'] = "VAT"
    vat_rows[' COD_ART_DOC'] = vat_rows[' COD_ART']
    vat_rows[' DESCR_ART'] = "VAT"
    vat_rows[' DESCR_ART_ESTESA'] = "VAT"
    vat_rows[' DESCRIZIONE_RIGA'] = "VAT"
    vat_rows[' PROGRESSIVO_RIGA'] = vat_rows[' PROGRESSIVO_RIGA'].astype(str) + "-3"
    vat_rows[' HSCODE'] = ""
    return vat_rows

# Funzione per la rimozione dei valori in "COD_FISCALE" basati su no_cod_fiscale.txt
def remove_cod_fiscale(df, no_cod_fiscale_list):
    for index, row in df.iterrows():
        cod_fiscale = row[' COD_FISCALE']
        if pd.isna(cod_fiscale):
            continue  # Salta se COD_FISCALE è NaN o vuoto
        cod_fiscale = str(cod_fiscale).strip().upper()  # Converte in maiuscolo per il confronto
        if cod_fiscale in no_cod_fiscale_list:
            df.at[index, ' COD_FISCALE'] = ""  # Svuota la cella se il valore è presente in no_cod_fiscale_list
        else:
            df.at[index, ' COD_FISCALE'] = cod_fiscale  # Mantieni il valore maiuscolo
    return df

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, delimiter=';', dtype={' PARTITA_IVA': str, ' NUM_DOC': str, ' CAP': str, ' COD_CLI_XMAG': str, ' HSCODE': str, ' TELEFONO1': str, ' COD_CLI': str, ' TIPO_CF': str})

    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Leggi il file no_cod_fiscale.txt
    try:
        with open('no_cod_fiscale.txt', 'r') as f:
            no_cod_fiscale_content = f.read().strip()
            # Assicurati che i nomi nel file siano tutti maiuscoli per il confronto
            no_cod_fiscale_list = [x.strip().upper() for x in no_cod_fiscale_content.split(';')]
    except Exception as e:
        st.error(f"Errore nella lettura di no_cod_fiscale.txt: {e}")
        no_cod_fiscale_list = []

    # Creazione di un dizionario per il mappaggio nome maiuscolo -> nome originale
    all_rags = list(df[' RAG_SOCIALE'].dropna().unique())
    name_mapping = {rag.upper(): rag for rag in all_rags}
    sorted_keys = sorted(name_mapping.keys())  # Chiavi ordinate del dizionario

    # Creazione di checkbox per selezionare più "RAG_SOCIALE"
    selected_rags_upper = [key for key in sorted_keys if st.checkbox(key, key=key)]

    # Applica il filtro utilizzando i nomi originali
    if selected_rags_upper:
        selected_rags = [name_mapping[rag] for rag in selected_rags_upper]
        df = df[df[' RAG_SOCIALE'].isin(selected_rags)]
    else:
        st.write("Nessuna selezione effettuata, visualizzati tutti i dati.")

    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC'])
    adjusted_rows = process_shipping_rows(unique_costs_rows, countrycode_dict)
    df_with_shipping = pd.concat([df, adjusted_rows], ignore_index=True)
    vat_rows = process_vat_rows(unique_costs_rows, countrycode_dict, df_with_shipping)
    final_df = pd.concat([df_with_shipping, vat_rows], ignore_index=True)

    # Rimuovi le righe con COD_ART uguale a 'SHIPPINGCOSTS0'
    final_df = final_df[final_df[' COD_ART'] != 'SHIPPINGCOSTS0']

    for index, row in final_df.iterrows():
        partita_iva_is_empty = pd.isna(row[' PARTITA_IVA']) or (isinstance(row[' PARTITA_IVA'], str) and not row[' PARTITA_IVA'].strip())
        if row[' NAZIONE'] in countrycode_dict and partita_iva_is_empty:
            iva_to_remove = countrycode_dict[row[' NAZIONE']]
            try:
                prezzo_con_iva = float(str(row[' PREZZO_1']).replace(",", "."))
                prezzo_senza_iva = prezzo_con_iva / (1 + iva_to_remove / 100)
                final_df.at[index, ' PREZZO_1'] = round(prezzo_senza_iva, 2)
            except Exception as e:
                st.error(f"Errore nella rimozione dell'IVA da 'PREZZO_1' per la riga {index}: {e}")

    # Ordina e aggiorna i progressivi
    final_df.sort_values(by=[' NUM_DOC', ' PROGRESSIVO_RIGA'], inplace=True)
    new_progressivo = (final_df.groupby([' NUM_DOC', ' PROGRESSIVO_RIGA']).ngroup() + 1)
    final_df[' PROGRESSIVO_RIGA'] = new_progressivo

    # Applica la funzione per rimuovere i valori da COD_FISCALE
    final_df = remove_cod_fiscale(final_df, no_cod_fiscale_list)

    # Elimina le righe "VAT" se "ALI_IVA" ha il valore "47"
    final_df = final_df[~((final_df[' ALI_IVA'] == 47) & (final_df[' COD_ART'] == "VAT"))]

    # Resto del codice per la generazione e il download del CSV
    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    st.write("Anteprima dei dati filtrati:", final_df)
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
