<?xml version="1.0" encoding="UTF-8"?>
<tileset name="enemies" tilewidth="32" tileheight="32" tilecount="5" columns="0">
 <grid orientation="orthogonal" width="1" height="1"/>
 <tile id="0" type="yellow">
  <properties>
   <property name="attack_power" type="float" value="10"/>
   <property name="attack_range" type="float" value="100"/>
   <property name="attack_speed" type="float" value="2"/>
   <property name="bullet" value="red"/>
   <property name="bullet_speed" type="float" value="10"/>
   <property name="hp" type="int" value="30"/>
   <property name="speed" type="float" value="1"/>
  </properties>
  <image width="32" height="28" source="../images/enemies/yellow.png"/>
 </tile>
 <tile id="1" type="beige">
  <properties>
   <property name="attack_power" type="float" value="30"/>
   <property name="attack_range" type="float" value="100"/>
   <property name="attack_speed" type="float" value="1"/>
   <property name="bullet" value="red"/>
   <property name="bullet_speed" type="float" value="20"/>
   <property name="hp" type="int" value="80"/>
   <property name="speed" type="float" value="0.7"/>
  </properties>
  <image width="32" height="31" source="../images/enemies/beige.png"/>
 </tile>
 <tile id="2" type="blue">
  <properties>
   <property name="attack_power" type="float" value="15"/>
   <property name="attack_range" type="float" value="50"/>
   <property name="attack_speed" type="float" value="1.5"/>
   <property name="bullet" value="red"/>
   <property name="bullet_speed" type="float" value="10"/>
   <property name="hp" type="int" value="100"/>
   <property name="speed" type="float" value="1.5"/>
  </properties>
  <image width="27" height="32" source="../images/enemies/blue.png"/>
 </tile>
 <tile id="3" type="green">
  <properties>
   <property name="attack_power" type="float" value="10"/>
   <property name="attack_range" type="float" value="100"/>
   <property name="attack_speed" type="float" value="2"/>
   <property name="bullet" value="red"/>
   <property name="bullet_speed" type="float" value="10"/>
   <property name="hp" type="int" value="30"/>
   <property name="speed" type="float" value="1"/>
  </properties>
  <image width="32" height="32" source="../images/enemies/green.png"/>
 </tile>
 <tile id="4" type="pink">
  <properties>
   <property name="attack_power" type="float" value="20"/>
   <property name="attack_range" type="float" value="100"/>
   <property name="attack_speed" type="float" value="1.5"/>
   <property name="bullet" value="red"/>
   <property name="bullet_speed" type="float" value="10"/>
   <property name="hp" type="int" value="30"/>
   <property name="speed" type="float" value="0.8"/>
  </properties>
  <image width="31" height="32" source="../images/enemies/pink.png"/>
 </tile>
</tileset>
