def create_user(request, form=None, backend=None, template_name='login.html', extra_context={}): 
    try:
        if not backend:
            backend = get_backend(request)
        if not form:
            form = backend.get_signup_form()
        if form.is_valid():
            status, message = backend.signup(form)
            messages.add_message(request, status, message)
        else:
            messages.add_message(request, messages.ERROR, form.errors)
    except (Invitation.DoesNotExist, ValueError), e:
        messages.add_message(request, messages.ERROR, e)
    #delete cookie
    return render_response(template_name,
                           form = LocalUserCreationForm(),
                           context_instance=get_context(request, extra_context))