#include<bits/stdc++.h>
#include<windows.h>
#include<conio.h>
#include<io.h>
using namespace std;
string stationName[200];
char option[1000];
int stationTot;
string trainCode="\0",arrT="\0",dptT="\0",arrS="\0",dptS="\0",ord="\0",spd="\0";
string input,info[20],currS="\0";
const string dic[]={"贵  阳北","重  庆西","End"};
const string dicF[]={"贵阳北","重庆西"};
void check(){
	for(int i=0;dic[i]!="End";i++){
		if(arrS==dic[i])arrS=dicF[i];
		if(dptS==dic[i])dptS=dicF[i];
	}
}

string utfCov(const char* str) {
	string result;WCHAR *strSrc;LPSTR szRes;
	int i=MultiByteToWideChar(CP_UTF8,0,str,-1,NULL,0);
	strSrc=new WCHAR[i+1];
	MultiByteToWideChar(CP_UTF8,0,str,-1,strSrc,i);
	i=WideCharToMultiByte(CP_ACP,0,strSrc,-1,NULL,0,NULL,NULL);
	szRes=new CHAR[i+1];
	WideCharToMultiByte(CP_ACP,0,strSrc,-1,szRes,i,NULL,NULL);
	result=szRes;delete[] strSrc;delete[] szRes;
	return result;
}
void crawler(){
	ifstream fin;ofstream fout;
	fout.open("train.txt",ios::out);
	for(int i=1;i<=stationTot;i++){
		sprintf(option,"curl -s \"https://train.hao86.com/%s/\" > tmp.txt",utfCov(stationName[i].c_str()).c_str());
		cout<<option<<endl;system(option);fin.open("tmp.txt",ios::in);
		int special=0;bool lop=1;
		const string sign="<th>查询站站序</th>";
		for(int type=1;type<=3&&lop;type++){
			while(lop){getline(fin,input);if(input==sign)break;if(input=="</html>")lop=0;}
			getline(fin,input);input.clear();
			while(lop){
				for(int j=1;j<=16;j++)getline(fin,info[j]);if(info[1]!="<tr>")break;
				trainCode="\0",arrT="\0",dptT="\0",arrS="\0",dptS="\0",ord="\0",spd="\0",currS="\0";
				if(info[16]!="</tr>")getline(fin,info[17]),special=0;
				else special=1;
				for(int j=0;info[3][j]!='<';j++)trainCode+=info[3][j];
				if(!special)for(int j=0;info[5][j]!='<';j++)spd+=info[5][j];
				for(int j=0;info[7-special][j]!='<';j++)dptS+=info[7-special][j];
				for(int j=0;info[10-special][j]!='<';j++)arrS+=info[10-special][j];
				for(int j=0,s=0;s<=2;j++){
					if(info[14-special][j]=='<'||info[14-special][j]=='>'){s++;continue;}
					if(s==2)arrT+=info[14-special][j];
				}
				for(int j=0;info[13-special][j]!='<';j++)currS+=info[13-special][j];
				for(int j=0,s=0;s<=2;j++){
					if(info[15-special][j]=='<'||info[15-special][j]=='>'){s++;continue;}
					if(s==2)dptT+=info[15-special][j];
				}
				for(int j=0,s=0;s<=2;j++){
					if(info[16-special][j]=='<'||info[16-special][j]=='>'){s++;continue;}
					if(s==2)ord+=info[16-special][j];
				}
				if(arrT=="----")arrT="0";if(dptT=="----")dptT="0";
				check();
				if(currS!=stationName[i])continue;
				if(spd=="高速"||trainCode[0]=='G')
					fout<<stationName[i]<<" "<<trainCode<<" "<<dptS<<" "<<arrS<<" "<<arrT<<" "<<dptT<<" "<<ord<<endl; 
			}
		}
		fin.close();
	}
	fout<<"0 0 0 0 0 0 0"<<endl;
}
void master(){
	ifstream fin;ofstream fout;
	//system("chcp 936");SetConsoleOutputCP(936);
	fin.open("station.txt",ios::in);
	while(true){fin>>stationName[++stationTot];if(stationName[stationTot]=="#")break;}
	stationTot--;fin.close();
}
int main(){
	master();
	crawler();
	return 0;
}