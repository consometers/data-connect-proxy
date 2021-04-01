# Référence Quoalise, protocole utilisé sur SEN3

*État d’avancement, décembre 2020*

Ce document présente l’état d’avancement du protocole de communication Quoalise, développé pour le chantier SEN – « Sensibilisation aux consommations d’énergie ».

Bien que chaque application ait sa spécificité (fournir un service à un citoyen ou une collectivité), chacune fonctionne à partir de données énergétiques, mesurées par des capteurs ou des fournisseurs d’énergie. L’objet de Quoalise est de standardiser un protocole de communication pour que chaque application parle la « même langue » pour échanger des données énergétiques.

De cette manière, un composant développé pour une certaine application sera plus facilement réutilisable par d’autres. Le travail de réflexion et de conception propre à l’échange de données énergétique est ainsi mutualisé (données à caractère personnel, données « chaudes »,  données « froides »,  données ouvertes, etc.). Les ressources économisées pourront être consacrées au domaine métier et à la spécificité de chaque application, comme l’expérience utilisateur, facturation ou la surveillance des installations.

Plus techniquement, Quoalise permet un échange de données entre serveurs pairs (appelés nœuds, au sens topologique) sans lien de subordination entre eux. Son but est de faciliter l’échange de données de consommation d’énergie au sein d’une fédération d’applications.

## Évolution du protocole

Le développement de Quoalise a débuté en 2019, au sein du chantier SEN, lors d’une phase de préfiguration permettant d’expérimenter et mettre à l’épreuve certains choix techniques. Cette phase est documentée sur le Wiki des Consometers, [Chantier SEN1 - Phase de POC](https://wiki.consometers.org/projets:chantier-sen1:poc).

Depuis juin 2020, d’autres acteurs de l’énergie et de l’échange de données ont été impliqués au développement de Quoalise. L’implémentation présentée ici a toutefois été développée avant la création de ce groupe, c’est donc une version de travail, un support permettant nos discussions.

## Implémentation de référence

Le premier composant développé en utilisant Quoalise permet d’accéder aux données de consommation de particuliers ayant un compteur communicant. Il utilise le service Data Connect d’Enedis. Ce composant, nommé « proxy Data Connect » constitue aujourd’hui l’implémentation de référence de Quoalise.

Il est développé avec le langage Python, disponible sur ce dépôt : <https://github.com/consometers/data-connect-proxy>

## Protocole basé sur XMPP

Lors de la phase de préfiguration du projet, XMPP avait été choisi, il répondait le mieux aux critères suivants :

- Communauté : le code logiciel, disponible publiquement, est fréquemment mis à jour. Les utilisateurs finaux sont nombreux et variés.
- Implémentations logicielles : l’existence d’implémentation dans différents langages, sous licence libre.
- Une structure est porteuse du protocole et de son évolution.
- Son utilisation peut être compatible avec le RGPD (en suivant notamment l’état de l’art sur la confidentialité des données).
- Extensible à notre cas d’usage : l’échange de données énergétiques.

Ce choix reste aujourd’hui largement pertinent.

De manière indépendante, un groupe de travail de l’IEEE a d’ailleurs choisi XMPP pour un projet de protocole standard sur l’Internet des objets. C’est un cas d’usage très proche du nôtre, le groupe de travail semble toujours actif, nous pourrions donc envisager un rapprochement entre ces deux protocoles.

- <https://standards.ieee.org/project/1451-99.html>
- <https://gitlab.com/IEEE-SA/XMPPI/IoT>

D’autres possibilités sont toujours étudiées, en particulier :

- HTTP et REST : le standard étant le plus utilisé aujourd’hui pour échanger des données de tout type, bien qu’il ne soit pas spécifiquement adapté à cet usage.
- Matrix : semblable à XMPP sur certains aspects. Moins mature, mais plus flexible pour une utilisation respectant l’état de l’art de la confidentialité des données, comme le chiffrement de bout en bout.
- Solid ou ActivityPub: deux projets très intéressants de Web décentralisé, le même potentiel de protocole « universel » que HTTP, tout en proposant une architecture décentralisée que nous privilégions. Ces projets sont également récents, il sont actuellement assez complexes à utiliser pour nos cas d’usage.

### Mise en relation des nœuds

Deux nœuds peuvent entrer en communication grâce à leurs adresses XMPP, appelées *JID*. Dans le cas du proxy Data Connect, il s’agit de `dataconnect-proxy@breizh-sen2.eu/proxy`. `breizh-sen2.eu` est un serveur XMPP hébergé par ALOEN pour le chantier SEN.

Pour utiliser ce proxy, un utilisateur pourrait utiliser n’importe quel compte XMPP. Il est toutefois vivement conseillé d’utiliser son propre serveur, puisque les données échangées sont déchiffrées par le serveur. Un serveur tiers pourrait donc accéder aux données personnelles échangées.

### Transmission de donnée par interrogation

Pour interroger le serveur et recevoir des données en réponse, la [XEP-0050: Ad-Hoc Commands](https://xmpp.org/extensions/xep-0050.html) est utilisée. Il est donc possible d’échanger avec le fournisseur de données à partir d’un client XMPP supportant cette extension, comme [Gajim](https://gajim.org/).

Plus concrètement un client peut envoyer l'`iq` suivant pour récupérer les données du point d’usage spécifié :

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

Si l’utilisateur est autorisé à accéder à ces données, le serveur les renvoie en réponse à l'`iq`, au format SENML :

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

- Les éléments non standards XMPP portent le namespace `urn:quoalise:0`
- Contrairement à la phase de préfiguration, les métadonnées ne sont pas incluses dans l’élément SENML, mais dans un élément `meta` dédié. Il n’existe pas encore de référence comportant toutes les meta données possibles.
- Les données sont renvoyées au format SENML :
  + `bt`: « base time, » timestamp en UTC (seconde)
  + `t`: offset en seconde à ajouter à `bt` pour chaque mesure
  + Pour les mesures concernant un intervalle de temps, comme une puissance moyenne sur 30 minutes, le timestamp correspond au début de la période.

Si une erreur survient, ou si l’utilisateur n’est pas autorisé, l’erreur est renvoyée en utilisant le mécanisme d’erreur de XMPP. Un élément y a été ajouté pour fournir une information métier.

```xml
<iq xml:lang="en" to="…" type="error" id="ab63a">
   <error type="cancel">
       <undefined-condition xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/>
       <text xmlns="urn:ietf:params:xml:ns:xmpp-stanzas">The requested period cannot be anterior to the meter&apos;s last activation date</text>
       <upstream-error xmlns="urn:quoalise:0" issuer="enedis-data-connect" code="ADAM-ERR0123" />
   </error>
</iq>
```

### Chaînage de consentement OAUTH2

Enedis permet à un consommateur équipé d’un compteur communicant de partager ses données de consommation à une application tierce. Pour ce faire, il doit suivre la procédure suivante :

- L’application tierce doit disposer d’une interface Web, disposer d’une structure juridique et avoir contractualisé avec Enedis
- Le consommateur clique sur un bouton dans l’application, accompagné d’une description sur la finalité du traitement de ces données à caractère personnel.
- Ce bouton envoie le consommateur sur son Espace client Enedis
- Dans son espace il peut autoriser Enedis à transmettre ses données à l’application tierce
- L’espace client Enedis renvoie finalement le consommateur sur l’application tierce
- Un code secret est transmis à l’application tierce, lui permettant de récupérer les données

Ce type de fonctionnement est assez courant sur les services en ligne, il s’agit donc d’un cas d’usage qui doit être supporté par Quoalise. Voici comment le proxy Data Connect permet à un utilisateur de recueillir le consentement de l’utilisateur sans disposer d’une interface Web.

Par XMPP et la [XEP-0050](https://xmpp.org/extensions/xep-0050.html) , l’utilisateur du proxy (une application) configure une page Web hébergée par le proxy Data Connect. Cette page sera affichée au consommateur avant qu’il ne soit renvoyé sur espace client Enedis, elle doit décrire le service proposé par l’application et décrire la finalité des traitements des données de consommation.

```xml
<iq xml:lang="fr" to="dataconnect-proxy-dev@breizh-sen2.eu/proxy" from="…" type="set" id="abbca">
   <command xmlns="http://jabber.org/protoc ol/commands" node="get_authorize_uri" action="execute">
      <x xmlns="jabber:x:data" type="submit">
         <field var="name" type="text-single">
            <value>Elec Expert Demo</value>
         </field>
         <field var="logo_url" type="text-single">
            <value>https://example.fr/logo.png</value>
         </field>
         <field var="description" type="text-multi">
            <value>&lt;p&gt;</value>
            <value>Nos experts analysent votre consommation d’électricité sur l’année précédente mesurée par votre compteur Linky.&lt;br/&gt;</value>
            <value>Lors d’un rendez-vous téléphonique, nous vous ferons part de nos recommandations pour mieux maîtriser votre consommation.</value>
            <value>&lt;/p&gt;</value>
            <value>&lt;p&gt;Retrouvez plus de détails sur notre &lt;a href="#"&gt;politique de confidentialité&lt;/a&gt;.&lt;/p&gt;</value>
         </field>
      </x>
   </command>
</iq>
```

- `description` est donné au format HTML
- `logo_url` est optionel. Il doit être renseigné par une URL, obligatoirement en https. Il sera affiché avec une largeur de 100 px.

Le serveur répond avec l’URL correspondant à la page générée.

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

Il est possible de rajouter à cette adresse la durée d’accès souhaitée et une autre adresse Web de redirection :

```
https://srv5.breizh-sen2.eu/dataconnect-proxy/authorize?id=ad35a140&duration=P1Y&redirect_uri=http%3A%2F%2Fperdu.com%3Fuser%3Dplop
```

En allant sur cette page, l’utilisateur pourra accéder à son espace Enedis. S’il exprime son consentement. Un message XMPP sera renvoyé à l’application tierce. Il sera redirigé sur l’adresse de redirection si elle a été fournie, sinon le proxy affichera juste un message de confirmation.

```
http://perdu.com?user=plop&usage_points=64975835695673,63695879465986,22315546958763
```

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

D’autres paramètres peuvent être utilisés sur l’adresse configurée. Dans le cas du proxy Data Connect, `test_client` est par exemple utilisé pour tester la page de consentement en mode bac à sable.

```
https://srv5.breizh-sen2.eu/dataconnect-proxy/authorize?id=ad35a140&duration=P1Y&test_client=0
```