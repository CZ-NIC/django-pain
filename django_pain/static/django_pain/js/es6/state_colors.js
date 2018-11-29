export function color_rows_by_state() {
    const rows = document.querySelectorAll('#result_list tr')
    rows.forEach(function(row) {
        const stateField = row.querySelector('th.field-detail_link div')
        if (stateField) {
            const state = stateField.className
            if (state === 'state_deferred') {
                row.classList.add('payment_deferred')
            }
            if (state === 'state_processed') {
                row.classList.add('payment_processed')
            }
        }
    })
}

document.addEventListener('DOMContentLoaded', color_rows_by_state)
