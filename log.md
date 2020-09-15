## Authorize

Client:

```xml
<iq xml:lang="fr" to="dataconnect-proxy@breizh-sen2.eu/proxy" from="…" type="set" id="abbca">
  <command xmlns="http://jabber.org/protocol/commands" action="execute" node="get_authorize_uri">
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
<iq xml:lang="fr" to="…" type="result" id="abbca">
  <command
    xmlns="http://jabber.org/protocol/commands" node="get_authorize_uri" sessionid="1591519295.244349-ce980c9e67e64e9382712f64355898aa" status="completed">
    <x
      xmlns="jabber:x:data" type="result">
      <title>Authorize URI</title>
      <field var="authorize_uri" type="text-single" label="Adresse pour recueillir le consentement">
        <value>https://srv5.breizh-sen2.eu/dataconnect-proxy/authorize?id=ad35a140</value>
      </field>
    </x>
  </command>
</iq>
```

Il est possible de rajouter à cette adresse une durée et un adresse de redirection :

```
https://srv5.breizh-sen2.eu/dataconnect-proxy/authorize?id=ad35a140&duration=P1Y&redirect_uri=http%3A%2F%2Fperdu.com%3Fuser%3Dplop
```

Quand l’utilisateur à exprimé son consentement, redirection web vers redirect uri + envoi d’un message xmpp

```
http://perdu.com?user=plop&usage_points=64975835695673,63695879465986,22315546958763
```

Serveur:

```xml
<message type="chat" to="…" id="1f72f82198b84deeaac85edbe43b024b" xml:lang="en">
  <origin-id xmlns="urn:xmpp:sid:0" id="1f72f82198b84deeaac85edbe43b024b"/>
  <body>Access granted for usage points 22516914714270</body>
  <x xmlns="https://consometers.org/dataconnect#authorize">
    <usage-point>22516914714270</usage-point>
    <state>ton_etat</state>
  </x>
</message>
```

Utiliser le paramètre `test_client` pour tester sur le bac à sable :

```
https://srv5.breizh-sen2.eu/dataconnect-proxy/authorize?id=ad35a140&duration=P1Y&test_client=0
```

Cela permet d’accéder aux profils clients de test Enedis :

`0`: Client qui ne possède qu’un seul point de livraison de consommation pour lequel il a activé la courbe de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.

`1`: Client qui ne possède qu’un seul point de livraison de consommation pour lequel il a activé la courbe de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service le 27 août 2019.

`2`: Client qui ne possède qu’un seul point de livraison de consommation pour lequel il n’a pas activé la courbe de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.

`3`: Client qui possède un point de livraison de consommation et un point de livraison de production pour lesquels il a activé les courbes de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et ses compteurs ont été mis en service au début du déploiement Linky.

`4`: Client qui possède qu’un  seul point de livraison de consommation pour lequel il a activé la courbe de charge.
Ses données présentent des « trous » de données les mardis et mercredis et son compteur a été mis en service au début
du déploiement Linky

`5`: Client qui possède qu’un seul point de livraison de production pour lequel il a activé la courbe de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.

`6`: Client qui possède un point de livraison d’ auto-consommation pour lequel il a activé la courbe de charge en production et en consommation.
Pour chaque point prélevé, lorsque la consommation est supérieur à la production les données de consommation remontées correspondent à la consommation moins la production et la production est nulle. Inversement lorsque la production est supérieure à la consommation.
Ses données sont remontées de manière exacte (sans « trou » de données) et son compteur a été mis en service au début du déploiement Linky.

`7`: Client qui possède trois points de livraison de consommation  pour lesquels il a activé les courbes de charge.
Ses données sont remontées de manière exacte (sans « trou » de données) et ses compteurs ont été mis en service au début du déploiement Linky.

`8`: Client qui donne son consentement mais le révoque immédiatement après l’avoir donné.

`9`: Client qui refuse systématiquement de donner son consentement.

## API Courbe de charge

Client:

```xml
<iq xml:lang="fr" to="dataconnect-proxy@breizh-sen2.eu/proxy" from="…" type="set" id="ab63a">
   <command xmlns="http://jabber.org/protocol/commands" node="get_load_curve" action="execute">
      <x xmlns="jabber:x:data" type="submit">
         <field var="usage_point_id" type="text-single">
            <value>10284856584123</value>
         </field>
         <field var="direction" type="list-single">
             <value>production</value>
         </field>
         <field var="start_date" type="text-single">
            <value>2020-09-14</value>
         </field>
         <field var="end_date" type="text-single">
            <value>2020-09-15</value>
         </field>
      </x>
   </command>
</iq>
```

Le champs `direction` peut prendre les valeurs `consumption` et `production`.

Le serveur renvoie les données en réponse à l'`iq`, au format SENML :

```xml
<iq xml:lang="fr" to="…" type="result" id="ab63a">
  <command xmlns="http://jabber.org/protocol/commands" node="get_load_curve" status="completed">
    <x xmlns="jabber:x:data" type="result">
      <title>Get production load curve data</title>
      <field var="result" type="fixed" label="production load curve for 10284856584123"><value>Success</value></field>
    </x>
    <quoalise xmlns="urn:quoalise:0">
      <data>
        <meta>
          <device type="electricity-meter">
            <identifier authority="enedis" type="prm" value="10284856584123" />
          </device>
          <measurement>
            <physical quantity="power" type="electrical" unit="W" />
            <business graph="load-profile" direction="production" />
            <aggregate type="average" />
            <sampling interval="1800" />
          </measurement>
        </meta>
        <sensml xmlns="urn:ietf:params:xml:ns:senml">
          <senml bn="urn:dev:prm:10284856584123_production_load" bt="1600041600" t="0" v="245" bu="W" />
          <senml t="1800" v="420" />
          <senml t="3600" v="367" />
          <senml t="5400" v="377" />
          <!-- … -->
        </sensml>
      </data>
    </quoalise>
  </command>
</iq>
```

`bt`: « base time, » timestamp en UTC (seconde)
`t`: offset en seconde à ajouter à `bt`

Ou si erreur :

```xml
<iq xml:lang="en" to="…" type="error" id="ab63a">
   <error type="cancel">
       <undefined-condition xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/>
       <text xmlns="urn:ietf:params:xml:ns:xmpp-stanzas">The requested period cannot be anterior to the meter&apos;s last activation date</text>
       <upstream-error xmlns="urn:quoalise:0" issuer="enedis-data-connect" code="ADAM-ERR0123" />
   </error>
</iq>
```

## API consommation / production quotidienne

Client :

```xml
<iq xml:lang="en" to="dataconnect-proxy-dev@breizh-sen2.eu/proxy" from="…" type="set" id="5c8f743b-0f90-4469-aadf-98a88834d273">
  <command xmlns="http://jabber.org/protocol/commands" node="get_daily" action="execute">
    <x xmlns="jabber:x:data" type="submit">
      <field var="usage_point_id" type="text-single" label="Usage point">
        <value>11453290002823</value>
      </field>
      <field var="direction" type="list-single">
        <value>consumption</value>
      </field>
      <field var="start_date" type="text-single">
        <value>2020-08-16</value>
      </field>
      <field var="end_date" type="text-single">
        <value>2020-08-31</value>
      </field>
    </x>
  </command>
</iq>
```

Serveur :

```xml
<iq xml:lang="en" to="…" type="result" id="5c8f743b-0f90-4469-aadf-98a88834d273">
  <command xmlns="http://jabber.org/protocol/commands" node="get_daily" sessionid="1600176040.6601713-4c7b5487477b48a5b7fdddd57bf8a651" status="completed">
    <x xmlns="jabber:x:data" type="result">
      <title>Get daily consumption</title>
      <field var="result" type="fixed" label="consumption load curve for 11453290002823">
        <value>Success</value>
      </field>
    </x>
    <quoalise xmlns="urn:quoalise:0">
      <data>
        <meta>
          <device type="electricity-meter">
            <identifier authority="enedis" type="prm" value="11453290002823" />
          </device>
          <measurement>
            <physical quantity="energy" type="electrical" unit="Wh" />
            <business direction="consumption" />
            <aggregate type="sum" />
            <sampling interval="86400" />
          </measurement>
        </meta>
        <sensml xmlns="urn:ietf:params:xml:ns:senml">
          <senml bn="urn:dev:prm:11453290002823_daily_consumption" bt="1597536000" t="0" v="16433" bu="Wh" />
          <senml t="86400" v="15081" />
          <senml t="172800" v="14664" />
           <!-- … -->
          <senml t="1209600" v="16330" />
        </sensml>
      </data>
    </quoalise>
  </command>
</iq>
```
