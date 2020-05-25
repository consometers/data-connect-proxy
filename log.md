## Authorize

Client:

```xml
<iq xml:lang="fr" to="dataconnect-proxy@breizh-sen2.eu/proxy" from="cyril_lugan@liberasys.com/PsiMac" type="set" id="ab06a">
  <command xmlns="http://jabber.org/protocol/commands" node="get_authorize_uri" sessionid="1590355777.5047667-81cbb30f79084eaaac912c1607bce060" action="complete">
    <x xmlns="jabber:x:data" type="submit">
      <field var="redirect_uri" type="text-single">
        <value>https://viriya.fr/redirect</value>
      </field>
      <field var="duration" type="text-single">
        <value>P1Y</value>
      </field>
      <field var="state" type="text-single">
        <value>ton_etat</value>
      </field>
    </x>
  </command>
</iq>
```

Serveur:

```xml
<iq xml:lang="fr" to="cyril_lugan@liberasys.com/PsiMac" type="result" id="ab06a">
  <command xmlns="http://jabber.org/protocol/commands" node="get_authorize_uri" sessionid="1590355777.5047667-81cbb30f79084eaaac912c1607bce060" status="completed">
    <x xmlns="jabber:x:data" type="result">
      <title>Authorize URI</title>
      <field var="authorize_uri" type="text-single" label="Adresse pour recueillir le consentement">
        <value>https://gw.hml.api.enedis.fr/dataconnect/v1/oauth2/authorize?client_id=50e853e5-20e4-44c5-8678-d35a473d7a60&amp;response_type=code&amp;duration=P1Y&amp;state=4d0572fd</value>
      </field>
    </x>
  </command>
</iq>
```

Quand l’utilisateur à exprimé son consentement, redirection web vers redirect uri + envoi d’un message xmpp

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
<message to="cyril_lugan@liberasys.com/PsiMac" id="c0f13c842c4c422586cf10994c9883e6" xml:lang="en">
  <origin-id xmlns="urn:xmpp:sid:0" id="c0f13c842c4c422586cf10994c9883e6"/>
  <body>{Données brutes en json}</body>
  <subject>Consumption load curve for 26584978546985</subject>
  <sensml xmlns="urn:ietf:params:xml:ns:senml">
    <senml n="urn:dev:prm:22516914714270_consumption_load" t="1590193800.0" v="2133" u="W"/>
    <senml n="urn:dev:prm:22516914714270_consumption_load" t="1590195600.0" v="2097" u="W"/>
    …
    <senml n="urn:dev:prm:22516914714270_consumption_load" t="1590278400.0" v="1465" u="W"/>
  </sensml>
</message>
```

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