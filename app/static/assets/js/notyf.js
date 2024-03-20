const notyf = new Notyf({
    types: [{
            type: 'warning',
            duration: 7000,
            background: 'linear-gradient(45deg, rgb(239, 253, 33), rgb(255, 0, 0))',
            dismissible: true,
            icon: {
                className: 'fas fa-exclamation-triangle',
                tagName: 'span',
                color: '#fff'
            },
        },
        {
            type: 'info',
            duration: 7000,
            background: '#515d8a',
            dismissible: true,
            icon: {
                className: 'fas fa-info-circle',
                tagName: 'span',
                color: '#fff'
            },
        },
        {
            type: 'error',
            duration: 7000,
            dismissible: true,
            icon: {
                className: 'fas fa-exclamation-triangle',
                tagName: 'span',
                color: '#fff'
            },
        },
        {
            type: 'success',
            duration: 7000,
            dismissible: true,
            icon: {
                className: 'fas fa-check-circle',
                tagName: 'span',
                color: '#fff'
            },
        },
    ]
});