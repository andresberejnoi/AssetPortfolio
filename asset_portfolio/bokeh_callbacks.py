from bokeh.models import CustomJS

# Create the custom JavaScript callback
callback1 = CustomJS(args=dict(s1=s1, div1=div1), code='''
    var ind = s1.selected.indices;
    if (String(ind) != '') {
        lifeboat = s1.data['Lifeboat'][ind];
        female = s1.data['female'][ind];
        male = s1.data['male'][ind];
        female_per = s1.data['female_per'][ind];
        male_per = s1.data['male_per'][ind];
        side = s1.data['Side'][ind];
        message = '<b>Lifeboat: ' + String(lifeboat) + ' (' + String(side) + ' side)' + '</b><br>Females: ' + String(female) + ' (' + String(female_per) +  '%)' + '<br>Males: ' + String(male) + ' (' + String(male_per) +  '%)' + '<br>Total: ' + String(female+male);
        div1.text = message;
    }
    else {
        div1.text = '';
    }
''')