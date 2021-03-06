from django.http import Http404
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.db.models import Q
from .models import Event
from users.models import UserData, UserDonation, UserAttending
from .utils import event_user_donation_list, event_user_donation_total, event_donation_total, event_donation_list, event_notify, event_user_family, event_attendee_donation_list, donation_total, event_big_donationers, big_donationer
from django.contrib import messages
from django.core.mail import send_mail
from notifications.signals import notify

"""
Display all Events
"""
def event_list_view(request):
    if not request.user.is_authenticated:
        return redirect('/users/login/')
        
    event_list = Event.objects.order_by('-start_date')
    donation_list = event_donation_list(event_list)

    user_data = UserData.objects.get(user=request.user)
    user_donation_list = event_user_donation_list(event_list, user_data)

    data_list = zip(event_list, donation_list, user_donation_list)
    notify_list = None
    notify_unread = None

    #ensure user is not anonymous when getting notifications
    if request.user.is_authenticated:
        notify_list = request.user.notifications.unread()[:5]



    # SEARCH FUNCTION
    query = request.GET.get("q")
    if query:
        event_list = event_list.filter(
            Q(start_date__icontains=query) |
            Q(end_date__icontains=query) |
            Q(event_name__icontains=query) |
            Q(event_location__icontains=query)
        ).distinct()
        donation_list = event_donation_list(event_list)
        data_list = zip(event_list, donation_list, user_donation_list)

    context = {
        'data_list': data_list,
        'user': request.user,
        'notify_list': notify_list,
    }

    return render(request, 'events/eventIndex.html', context)

"""
Display all information about an event 
"""
def event_view(request, event_id):
    #get event specified in url
    try:
        event = Event.objects.get(id=event_id)
        donation = event_donation_total(event)
        user_data = UserData.objects.get(user=request.user)
        user_donations = 0

        #create a list of family member numbers based on informaion in the attendee database
        registered_attending = [(i.family+1) for i in UserAttending.objects.filter(event=event)]
        #get grand total of all attendees (including family members)
        registered_attending = sum(registered_attending)

        num_attending = registered_attending
        #use estemated interrest if users attending it too low for accurate price estimation
        if event.event_estemated_interrest > num_attending:
            num_attending = event.event_estemated_interrest

        #estemate ticket cost based on current donations and attending members
        #also ensure number isn't negative
        if not event.honor_event:
            ticket = max(0,(event.event_cost - donation) / num_attending)
        else: #change calculation for honor events to spread cost to all users
            ticket = max(0,(event.event_cost - donation) / (UserData.objects.all().count() - event_big_donationers(UserData.objects.all())))

        is_attending = None
        is_volunteering = None
        is_big_donationer = None
        notify_list = None
        notify_unread = None

        #ensure user is not anonymous
        if request.user.is_authenticated:
            #test if user is attending or volunteering for the event
            data = UserData.objects.get(user=request.user)
            is_attending = Event.objects.filter(userattending__user=data, id=event_id).exists()
            is_volunteering = UserData.objects.filter(user=request.user, events_volunteering__id=event_id).exists()
            is_big_donationer = big_donationer(data)
            user_donations = donation_total(data)
            #get notifications
            notify_list = request.user.notifications.unread()[:5]

    except Event.DoesNotExist:
        raise Http404("Event does not exist")

    context = {
        'event': event,
        'donation': donation,
        'user_donations': user_donations,
        'user': request.user,
        'is_attending': is_attending,
        'is_volunteering': is_volunteering,
        'is_big_donationer': is_big_donationer,
        'notify_list': notify_list,
        'registered_attendance': registered_attending,
        'expected_attendance': num_attending,
        'ticket': "{0:.2f}".format(ticket),
        'admin_url': event.get_admin_url(),
    }

    return render(request, 'events/eventPage.html', context)

"""
Add user to event attendee table
"""
def event_attend_view(request, event_id, option):
    amount = request.POST.get('amount', 0)

    if not request.user.is_authenticated:
        return redirect('/users/login')

    else:
        try:
            event = Event.objects.get(id=event_id)
            user = UserData.objects.get(user=request.user)

            if option == "1": #create
                #ensure user is not already attending
                if UserAttending.objects.filter(user=user, event=event).exists():
                    return redirect('/events/' + event_id)

                attendingUser = UserAttending(user=user, event=event, family=amount)
                attendingUser.save()
                event_notify(request, event, "You are attending", "is attending")

            
            if option == "2": #delete
                attendingUser = UserAttending.objects.get(user=user, event=event)
                attendingUser.delete()

        except Event.DoesNotExist:
            raise Http404("Event does not exist")

    return redirect('/events/' + event_id)

"""
Add a donation to the event
"""
def event_donate_view(request, event_id):
    amount = request.POST.get('amount', 0)

    if not request.user.is_authenticated:
        return redirect('/users/login')

    else:
        try:
            event = Event.objects.get(id=event_id)
            user = UserData.objects.get(user=request.user)

            donation = UserDonation(user=user, event=event, donation=amount)
            donation.save()
            event_notify(request, event, "You are donating to", "is donating to")

        except Event.DoesNotExist:
            raise Http404("Event does not exist")

        except UserData.DoesNotExist:
            raise Http404("Missing user data! what?!")

    #event_list = Event.objects.order_by('-start_date')[:5]

    return redirect('/events/')

"""
Add user to volunteer table
"""
def event_volunteer_view(request, event_id, option):
    if not request.user.is_authenticated:
        return redirect('/users/login')

    else:
        try:
            event = Event.objects.get(id=event_id)
            
            if option == "1": #create
                #make sure user is not already volunteer for the event this event
                if Event.objects.filter(id=event_id, userdata__user=request.user).exists():
                    return redirect('/events/' + event_id)

                user_voluntee = UserData.objects.get(user=request.user)
                user_voluntee.events_volunteering.add(event)
                user_voluntee.save()
                event_notify(request, event, "You are volunteering for", "is volunteering for")

            if option == "2": #delete
                user_voluntee = UserData.objects.get(user=request.user)
                user_voluntee.events_volunteering.remove(event)
                user_voluntee.save()

        except Event.DoesNotExist:
            raise Http404("Event does not exist")

    #event_list = Event.objects.order_by('-start_date')[:5]
    
    return redirect('/events/' + event_id)

"""
Display a list of all volunteers
"""
def event_volunteer_list_view(request, event_id):
    notify_list = None
    #get event specified in url
    try:
        volunteers = User.objects.filter(userdata__events_volunteering__id=event_id)

    except Event.DoesNotExist:
        raise Http404("Event does not exist")

    #ensure user is not anonymous when getting notifications
    if request.user.is_authenticated:
        notify_list = request.user.notifications.unread()[:5]

    context = {
        'user_list': volunteers,
        'user': request.user,
        'notify_list': notify_list,
    }

    return render(request, 'events/eventUsers.html', context)

"""
Display a list of all attendees
"""
def event_attendee_list_view(request, event_id):
    notify_list = None
    #get event specified in url
    try:
        event = Event.objects.get(id=event_id)

        user_data_list = UserData.objects.filter(userattending__event__id=event_id)

        attending_family_list = event_user_family(event, user_data_list)

        donation_list = event_attendee_donation_list(event, user_data_list)

        data_list = zip(user_data_list, attending_family_list, donation_list)

    except Event.DoesNotExist:
        raise Http404("Event does not exist")

    #ensure user is not anonymous when getting notifications
    if request.user.is_authenticated:
        notify_list = request.user.notifications.unread()[:5]

    context = {
        'user': request.user,
        'data_list': data_list,
        'notify_list': notify_list,
    }

    return render(request, 'events/eventAttendees.html', context)

"""
Send a notification to all members to donate the an event
"""
def event_notify_donations_view(request, event_id):
    notify.send(request.user, recipient=request.user, verb="/events/" + event_id, description='Requesting donations for event: ' + Event.objects.get(id=event_id).event_name)

    return redirect('/events/'+event_id)

"""
Serve a event creation form and handle event creation requests
"""
def event_create_view(request):

    #ensure user is an admin when creating events
    if not request.user.is_superuser:
        return redirect('/events')

    if request.method == 'POST':
        form = EventCreateForm(request.POST)

        if form.is_valid():
            event = form.save()
            send_mail(
                'Registration successful',
                'Thanks for registering',
                'ifb299dummyemail@gmail.com',
                ['ifb299dummyemail@gmail.com'],
                fail_silently=False,
            )

            return redirect('/events')

    else:
        form = EventCreateForm()

    notify_list = None

    #ensure user is not anonymous when getting notifications
    if request.user.is_authenticated:
        notify_list = request.user.notifications.unread()[:5]
        
    context = {
        'form': form,
        'user': request.user,
        'notify_list': notify_list,
    }

    return render(request, 'events/eventCreate.html', context)

"""
Mark all user notifications as read
"""
def event_mark_all_view(request):
    #ensure request is a post request
    if request.method == 'POST':
        request.user.notifications.unread().mark_all_as_read()

    return redirect('/events/')




