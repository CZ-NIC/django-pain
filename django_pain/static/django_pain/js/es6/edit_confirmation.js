export function confirm_edit(event) {
    const language = document.documentElement.lang
    let message = 'Are you sure you want to proceed?'
    if (language === 'cs') {
        message = 'Jste si jist, že chcete pokračovat?'
    }
    const result = confirm(message)
    if (result === false) {
        event.preventDefault()
    }
}

document.addEventListener('DOMContentLoaded', function() {
    document.querySelector('#bankpayment_form').addEventListener('submit', confirm_edit)
})
