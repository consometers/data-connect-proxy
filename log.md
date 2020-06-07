## Authorize

Client:

```xml
<iq xml:lang="fr" to="dataconnect-proxy@breizh-sen2.eu/proxy" from="cyril_lugan@liberasys.com/PsiMac" type="set" id="abbca">
  <command xmlns="http://jabber.org/protocol/commands" action="complete" node="get_authorize_uri" sessionid="1591519295.244349-ce980c9e67e64e9382712f64355898aa">
    <x xmlns="jabber:x:data" type="submit">
      <field var="name" type="text-single">
        <value>Elec Expert Demo</value>
      </field>
      <field var="service" type="text-multi">
        <value>Nos experts analysent votre consommation d’électricité sur l’année précédente mesurée par votre compteur Linky.</value>
        <value>Lors d’un rendez-vous téléphonique, nous vous ferons part de nos recommandations pour mieux maîtriser votre consommation.</value>
      </field>
      <field var="processings" type="text-multi">
        <value>Analyse votre consommation d’électricité</value>
        <value>Affichage de graphiques</value>
      </field>
    </x>
  </command>
</iq>
```

Serveur:

```xml
<iq xml:lang="fr" to="cyril_lugan@liberasys.com/PsiMac" type="result" id="abbca">
  <command
    xmlns="http://jabber.org/protocol/commands" node="get_authorize_uri" sessionid="1591519295.244349-ce980c9e67e64e9382712f64355898aa" status="completed">
    <x
      xmlns="jabber:x:data" type="result">
      <title>Authorize URI</title>
      <field var="authorize_uri" type="text-single" label="Adresse pour recueillir le consentement">
        <value>http://localhost:3000/authorize?id=ad35a140</value>
      </field>
    </x>
  </command>
</iq>
```

Il est possible de rajouter à cette adresse une durée et un adresse de redirection:

```
http://localhost:3000/authorize?id=ad35a140&duration=P1Y&redirect_uri=http%3A%2F%2Fperdu.com%3Fuser%3Dplop
```

Quand l’utilisateur à exprimé son consentement, redirection web vers redirect uri + envoi d’un message xmpp

```
http://perdu.com?user=plop&usage_points=64975835695673,63695879465986,22315546958763
```

Serveur:

```xml
<message type="chat" to="cyril_lugan@liberasys.com" id="1f72f82198b84deeaac85edbe43b024b" xml:lang="en">
  <origin-id xmlns="urn:xmpp:sid:0" id="1f72f82198b84deeaac85edbe43b024b"/>
  <body>Access granted for usage points 22516914714270</body>
  <x xmlns="https://consometers.org/dataconnect#authorize">
    <usage-point>22516914714270</usage-point>
    <state>ton_etat</state>
  </x>
</message>
```

## API consumtion curve

Client:

```xml
<iq xml:lang="fr" to="dataconnect-proxy@breizh-sen2.eu/proxy" from="cyril_lugan@liberasys.com/PsiMac" type="set" id="ab63a">
   <command xmlns="http://jabber.org/protocol/commands" node="get_consumption_load_curve" sessionid="1590408196.4231362-f128dbc37646459fbc1a371b50613e52" action="complete">
      <x xmlns="jabber:x:data" type="submit">
         <field var="usage_point_id" type="text-single">
            <value>26584978546985</value>
         </field>
         <field var="start_date" type="text-single">
            <value>2020-05-20</value>
         </field>
         <field var="end_date" type="text-single">
            <value>2020-05-21</value>
         </field>
      </x>
   </command>
</iq>
```

Serveur:

```xml
<message to="cyril_lugan@liberasys.com" id="62b5efaae4444b488c3b2e48a22535bd" xml:lang="en">
  <origin-id
    xmlns="urn:xmpp:sid:0" id="62b5efaae4444b488c3b2e48a22535bd" />
    <subject>Consumption load curve for 22516914714270</subject>
    <data
      xmlns="urn:quoalise:sen2:load_curve">
      <sensml
        xmlns="urn:ietf:params:xml:ns:senml">
        <senml bn="urn:dev:prm:22516914714270_consumption_load" bt="1590969600.0" t="1800" v="1616" u="W" />
        <senml t="3600" v="1742" u="W" />
        <senml t="5400" v="1689" u="W" />
        <senml t="7200" v="1782" u="W" />
        <!-- … -->
        <senml t="84600" v="1597" u="W" />
        <senml t="86400" v="2062" u="W" />
      </sensml>
    </data>
  </message>
```

bt: « base time, » timestamp en UTC (seconde)
t: offset en seconde à ajouter à bt
bn: « base name, » nom à utiliser pour toutes les entrées suivantes

Serveur:

```xml
<iq xml:lang="fr" to="cyril_lugan@liberasys.com/PsiMac" type="result" id="ab09a">
  <command xmlns="http://jabber.org/protocol/commands" node="get_consumption_load_curve" sessionid="1590355810.9193444-f78d9adfa5084a06ba7e99e5a8dea070" status="completed"/>
</iq>
```

Ou si erreur

Serveur:

```xml
<iq xml:lang="fr" to="cyril_lugan@liberasys.com/PsiMac" type="result" id="ab3ba">
  <command xmlns="http://jabber.org/protocol/commands" node="get_consumption_load_curve" sessionid="1590358216.588861-5b1fae28750f4e93a2d36172cde882c1" status="completed">
    <note type="error">{
    "error": "STM-ERR-0000020",
    "error_description": "no measure found for this usage point"
}</note>
  </command>
</iq>
```