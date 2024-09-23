import streamlit as st
import pandas as pd
import io

# Funzione per processare le righe di spedizione
def process_shipping_rows(rows, countrycode_dict):
    adjusted_rows = []  # Lista per memorizzare solo le righe valide
    errors = []  # Lista per memorizzare gli errori

    for index, row in rows.iterrows():
        try:
            costo_spedizione = float(row[' COSTI_SPEDIZIONE'].strip().replace(',', '.'))
        except ValueError as ve:
            errors.append(f"Valore non valido per COSTI_SPEDIZIONE nella riga {index + 1}: {row[' COSTI_SPEDIZIONE']} - {ve}")
            continue

        # Se il costo di spedizione è zero, non aggiungere la riga
        if costo_spedizione == 0:
            continue

        nazione = row[' NAZIONE']

        # Escludiamo i clienti italiani (NAZIONE == 86) dalle modifiche
        if nazione == '86':
            continue  # Ignoriamo completamente qualsiasi modifica per l'Italia

        # Procediamo con la modifica solo per clienti non italiani
        if nazione in countrycode_dict:
            iva = countrycode_dict[nazione]
            try:
                costo_senza_iva = costo_spedizione / (1 + iva / 100)
                formatted_price = round(costo_senza_iva, 2)
                row[' PREZZO_1'] = formatted_price
            except Exception as e:
                errors.append(f"Errore nella riga {index + 1}: {e}")
                continue  # Se c'è un errore, passa alla prossima riga

        row[' COD_ART'] = f"SHIPPINGCOSTS{costo_spedizione}"
        row[' COD_ART_DOC'] = row[' COD_ART']
        row[' DESCR_ART'] = "Shipping Costs"
        row[' DESCR_ART_ESTESA'] = "Shipping Costs"
        row[' DESCRIZIONE_RIGA'] = "Shipping Costs"
        row[' PROGRESSIVO_RIGA'] = f"{row[' PROGRESSIVO_RIGA']}-2"
        row[' HSCODE'] = ""  # Lascia vuota la colonna HSCODE

        adjusted_rows.append(row.copy())  # Aggiungi solo le righe valide

    # Stampa gli errori
    for error in errors:
        st.error(error)

    # Restituisci solo le righe valide
    return pd.DataFrame(adjusted_rows)

# Funzione per processare le righe IVA
def process_vat_rows(rows, countrycode_dict, df_original):
    vat_rows = rows.copy()
    vat_rows = vat_rows[vat_rows[' NAZIONE'].astype(str) != "86"]  # Escludiamo l'Italia
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

# Titolo dell'applicazione Streamlit
st.title('Modifica File CSV per Costi di Spedizione e IVA')

# Caricamento del file tramite drag-and-drop
uploaded_file = st.file_uploader("Carica il file CSV", type='csv')

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, delimiter=';')

    try:
        countrycode_df = pd.read_csv('countrycode.txt', delimiter=';', header=None)
        countrycode_dict = dict(zip(countrycode_df[0], countrycode_df[2]))
    except Exception as e:
        st.error(f"Errore nella lettura di countrycode.txt: {e}")
        countrycode_dict = {}

    # Manteniamo una copia dei prezzi originali per i clienti italiani
    df['PREZZO_1_ORIGINALE'] = df[' PREZZO_1']
    
    costs_rows = df[df[' COSTI_SPEDIZIONE'] != 0]
    unique_costs_rows = costs_rows.drop_duplicates(subset=[' NUM_DOC'])
    adjusted_rows = process_shipping_rows(unique_costs_rows, countrycode_dict)
    df_with_shipping = pd.concat([df, adjusted_rows], ignore_index=True)
    vat_rows = process_vat_rows(unique_costs_rows, countrycode_dict, df_with_shipping)
    final_df = pd.concat([df_with_shipping, vat_rows], ignore_index=True)

    for index, row in final_df.iterrows():
        partita_iva_is_empty = pd.isna(row[' PARTITA_IVA']) or (isinstance(row[' PARTITA_IVA'], str) and not row[' PARTITA_IVA'].strip())

        # Modifica: non scorporare l'IVA per i clienti italiani
        if row[' NAZIONE'] == '86':
            # Reinseriamo il prezzo originale per l'Italia
            final_df.at[index, ' PREZZO_1'] = row['PREZZO_1_ORIGINALE']
            continue  # Salta qualsiasi elaborazione

        if row[' NAZIONE'] in countrycode_dict and partita_iva_is_empty:
            iva_to_remove = countrycode_dict[row[' NAZIONE']]
            try:
                prezzo_con_iva = float(str(row[' PREZZO_1']).replace(",", "."))
                prezzo_senza_iva = prezzo_con_iva / (1 + iva_to_remove / 100)
                final_df.at[index, ' PREZZO_1'] = round(prezzo_senza_iva, 2)
            except Exception as e:
                st.error(f"Errore nella rimozione dell'IVA da 'PREZZO_1' per la riga {index}: {e}")

    final_df.sort_values(by=[' NUM_DOC', ' PROGRESSIVO_RIGA'], inplace=True)

    new_progressivo = (final_df.groupby([' NUM_DOC', ' PROGRESSIVO_RIGA'])
                      .ngroup() + 1)
    final_df[' PROGRESSIVO_RIGA'] = new_progressivo

    csv = final_df.to_csv(sep=';', index=False, float_format='%.2f').encode('utf-8').decode('utf-8').replace('.', ',').encode('utf-8')

    st.write("Anteprima dei dati:", final_df)
    st.download_button(
        label="Scarica il CSV modificato",
        data=io.BytesIO(csv),
        file_name='modified_CLIARTFATT.csv',
        mime='text/csv',
    )
