

#REQUERIMENTOS:
##Basta ter instalado no sistema o software 'sct' :
##sudo "sudo apt install sct" E as bibliotecas 'time' e 'subprocess' do Python.


##Script criado (em Python) para substituir os filtros de luz azul do Debian 11 (os quais não funcionaram na minha máquina, devido (acredito eu) à incompatibilidade com o WayLand ). 


##Colei o Script na pasta /opt , dei-lhe permissão de executável com o comando 'chmod +x' , e uma extensão .sh para ser reconhecido pelo kernel.
##Configurei-o para iniciar junto ao sistema. É um software extremamente simples, fiz poucas modificações desde que comecei a usar, mas, para mudar as temperaturas de tela de acordo com suas necessidades, basta modificar os valores a frente do comando 'sct' em 'subprocess.call'. 
