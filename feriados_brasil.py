import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Union, Tuple
import logging

logger = logging.getLogger(__name__)

class FeriadosBrasil:
    """
    Classe para gerenciar feriados brasileiros e datas especiais
    
    Inclui:
    - Feriados nacionais fixos (Natal, Ano Novo, etc.)
    - Feriados móveis (Carnaval, Páscoa, etc.)
    - Datas comerciais (Black Friday, Cyber Monday, etc.)
    """
    
    FERIADOS_FIXOS = {
        # Data no formato MM-DD
        "01-01": "Ano Novo",
        "04-21": "Tiradentes",
        "05-01": "Dia do Trabalho",
        "09-07": "Independência",
        "10-12": "Nossa Senhora Aparecida",
        "11-02": "Finados",
        "11-15": "Proclamação da República",
        "12-25": "Natal"
    }
    
    DATAS_COMERCIAIS = {
        # Black Friday (última sexta-feira de novembro)
        "black_friday": {"descrição": "Black Friday", "mês": 11, "dia_semana": 4, "semana": -1},
        # Cyber Monday (primeira segunda-feira após a Black Friday)
        "cyber_monday": {"descrição": "Cyber Monday", "mês": 11, "dia_semana": 0, "semana": -1, "ajuste": 3},
        # Véspera de Natal
        "vespera_natal": {"descrição": "Véspera de Natal", "mês": 12, "dia": 24},
        # Véspera de Ano Novo
        "vespera_ano_novo": {"descrição": "Véspera de Ano Novo", "mês": 12, "dia": 31}
    }
    
    def __init__(self, anos: List[int], incluir_feriados_fixos: bool = True, 
                 incluir_moveis: bool = True, incluir_comerciais: bool = True):
        """
        Inicializa o gerenciador de feriados brasileiros
        
        Args:
            anos: Lista de anos para calcular os feriados
            incluir_feriados_fixos: Se True, inclui feriados nacionais fixos
            incluir_moveis: Se True, inclui feriados móveis (Carnaval, Páscoa, etc.)
            incluir_comerciais: Se True, inclui datas comerciais (Black Friday, etc.)
        """
        self.anos = anos
        self.incluir_feriados_fixos = incluir_feriados_fixos
        self.incluir_moveis = incluir_moveis
        self.incluir_comerciais = incluir_comerciais
        self.feriados = self._gerar_feriados()
    
    def _calcular_pascoa(self, ano: int) -> datetime:
        """
        Calcula a data da Páscoa para um determinado ano usando o algoritmo de Butcher
        
        Args:
            ano: Ano para calcular a Páscoa
            
        Returns:
            Data da Páscoa como objeto datetime
        """
        a = ano % 19
        b = ano // 100
        c = ano % 100
        d = b // 4
        e = b % 4
        f = (b + 8) // 25
        g = (b - f + 1) // 3
        h = (19 * a + b - d - g + 15) % 30
        i = c // 4
        k = c % 4
        l = (32 + 2 * e + 2 * i - h - k) % 7
        m = (a + 11 * h + 22 * l) // 451
        month = (h + l - 7 * m + 114) // 31
        day = ((h + l - 7 * m + 114) % 31) + 1
        return datetime(ano, month, day)
    
    def _calcular_feriados_moveis(self, ano: int) -> Dict[str, datetime]:
        """
        Calcula os feriados móveis para um determinado ano
        
        Args:
            ano: Ano para calcular os feriados móveis
            
        Returns:
            Dicionário com os feriados móveis
        """
        feriados_moveis = {}
        
        # Páscoa (base para vários outros feriados)
        pascoa = self._calcular_pascoa(ano)
        feriados_moveis["Páscoa"] = pascoa
        
        # Carnaval (terça-feira, 47 dias antes da Páscoa)
        carnaval = pascoa - timedelta(days=47)
        feriados_moveis["Carnaval"] = carnaval
        
        # Segunda de Carnaval
        feriados_moveis["Segunda de Carnaval"] = carnaval - timedelta(days=1)
        
        # Sexta-feira Santa
        feriados_moveis["Sexta-feira Santa"] = pascoa - timedelta(days=2)
        
        # Corpus Christi (60 dias após a Páscoa)
        feriados_moveis["Corpus Christi"] = pascoa + timedelta(days=60)
        
        return feriados_moveis
    
    def _calcular_data_comercial(self, ano: int, config: Dict) -> Optional[datetime]:
        """
        Calcula datas comerciais como Black Friday
        
        Args:
            ano: Ano para calcular a data
            config: Configuração da data comercial
            
        Returns:
            Data como objeto datetime ou None se não for possível calcular
        """
        if "dia" in config:
            # Data fixa no mês
            return datetime(ano, config["mês"], config["dia"])
        
        if "dia_semana" in config:
            # Data baseada em dia da semana (ex: última sexta-feira do mês)
            mes = config["mês"]
            dia_semana = config["dia_semana"]  # 0=segunda, 6=domingo
            semana = config["semana"]  # -1 = última semana, 1 = primeira semana
            
            # Encontrar todas as ocorrências do dia da semana no mês
            if semana > 0:
                # Primeiro dia do mês
                data = datetime(ano, mes, 1)
                # Avançar até o primeiro dia da semana desejado
                while data.weekday() != dia_semana:
                    data += timedelta(days=1)
                # Avançar para a semana desejada
                data += timedelta(days=7 * (semana - 1))
            else:
                # Último dia do mês
                if mes == 12:
                    data = datetime(ano + 1, 1, 1) - timedelta(days=1)
                else:
                    data = datetime(ano, mes + 1, 1) - timedelta(days=1)
                # Retroceder até o último dia da semana desejado
                while data.weekday() != dia_semana:
                    data -= timedelta(days=1)
                # Retroceder para a semana desejada (partindo do final)
                data -= timedelta(days=7 * (abs(semana) - 1))
            
            # Aplicar ajuste, se houver (ex: Cyber Monday = 3 dias após a Black Friday)
            if "ajuste" in config:
                data += timedelta(days=config["ajuste"])
                
            return data
        
        return None
    
    def _gerar_feriados(self) -> pd.DataFrame:
        """
        Gera um DataFrame com todos os feriados para os anos especificados
        
        Returns:
            DataFrame com os feriados
        """
        feriados = []
        
        for ano in self.anos:
            # Feriados fixos
            if self.incluir_feriados_fixos:
                for data, descricao in self.FERIADOS_FIXOS.items():
                    mes, dia = map(int, data.split("-"))
                    data_feriado = datetime(ano, mes, dia)
                    feriados.append({
                        "data": data_feriado,
                        "descricao": descricao,
                        "tipo": "fixo",
                        "lower_window": -1,  # 1 dia antes
                        "upper_window": 1    # 1 dia depois
                    })
            
            # Feriados móveis
            if self.incluir_moveis:
                feriados_moveis = self._calcular_feriados_moveis(ano)
                for descricao, data_feriado in feriados_moveis.items():
                    windows = {
                        "Carnaval": (-2, 1),  # começa 2 dias antes, termina 1 dia depois
                        "Segunda de Carnaval": (-1, 2),  # 1 dia antes e 2 dias depois
                        "Páscoa": (-2, 1),  # Começa na Sexta Santa
                        "Sexta-feira Santa": (0, 2)  # Até o domingo de Páscoa
                    }
                    
                    lower, upper = windows.get(descricao, (-1, 1))
                    
                    feriados.append({
                        "data": data_feriado,
                        "descricao": descricao,
                        "tipo": "movel",
                        "lower_window": lower,
                        "upper_window": upper
                    })
            
            # Datas comerciais
            if self.incluir_comerciais:
                for nome, config in self.DATAS_COMERCIAIS.items():
                    data_comercial = self._calcular_data_comercial(ano, config)
                    if data_comercial:
                        # Para Black Friday, considerar 1 semana antes (promoções antecipadas)
                        if nome == "black_friday":
                            lower_window = -7
                            upper_window = 3  # Até Cyber Monday
                        else:
                            lower_window = -1
                            upper_window = 1
                            
                        feriados.append({
                            "data": data_comercial,
                            "descricao": config["descrição"],
                            "tipo": "comercial",
                            "lower_window": lower_window,
                            "upper_window": upper_window
                        })
        
        # Converter para DataFrame
        df = pd.DataFrame(feriados)
        
        # Ordenar por data
        if not df.empty:
            df = df.sort_values("data")
        
        return df
    
    def obter_dataframe_prophet(self) -> pd.DataFrame:
        """
        Retorna um DataFrame no formato compatível com Prophet
        
        Returns:
            DataFrame com as colunas 'ds', 'holiday', 'lower_window', 'upper_window'
        """
        if self.feriados.empty:
            return pd.DataFrame(columns=['ds', 'holiday', 'lower_window', 'upper_window'])
        
        df_prophet = pd.DataFrame({
            'ds': self.feriados['data'],
            'holiday': self.feriados['descricao'],
            'lower_window': self.feriados['lower_window'],
            'upper_window': self.feriados['upper_window']
        })
        
        return df_prophet
    
    def obter_ajustes_feriados(self) -> Dict[str, float]:
        """
        Retorna um dicionário com os ajustes sugeridos para cada tipo de feriado
        para uso com o ModeloAjustado
        
        Returns:
            Dicionário no formato {data_str: fator_ajuste}
        """
        ajustes = {}
        
        # Definir ajustes padrão para feriados
        ajustes_por_tipo = {
            "Natal": 1.5,             # +50% no Natal
            "Véspera de Natal": 1.8,  # +80% na véspera
            "Black Friday": 2.5,      # +150% na Black Friday
            "Cyber Monday": 1.8,      # +80% na Cyber Monday
            "Carnaval": 0.7,          # -30% no Carnaval (queda em alguns setores)
            "Segunda de Carnaval": 0.8, # -20% na Segunda de Carnaval
            "Ano Novo": 0.7,          # -30% no Ano Novo
            "Véspera de Ano Novo": 0.9 # -10% na véspera de Ano Novo
        }
        
        # Aplicar ajustes
        for _, row in self.feriados.iterrows():
            data_str = row['data'].strftime('%Y-%m-%d')
            descricao = row['descricao']
            
            if descricao in ajustes_por_tipo:
                ajustes[data_str] = ajustes_por_tipo[descricao]
        
        return ajustes
    
    def verificar_feriado(self, data: Union[str, datetime]) -> Tuple[bool, Optional[str]]:
        """
        Verifica se uma data é feriado
        
        Args:
            data: Data a ser verificada (string 'YYYY-MM-DD' ou objeto datetime)
            
        Returns:
            Tupla (é_feriado, descrição_do_feriado)
        """
        if isinstance(data, str):
            data = pd.to_datetime(data)
        
        # Verificar se a data está no DataFrame de feriados
        for _, row in self.feriados.iterrows():
            feriado_data = row['data']
            lower_window = row['lower_window']
            upper_window = row['upper_window']
            
            # Verificar se a data está dentro da janela do feriado
            delta_dias = (data - feriado_data).days
            if lower_window <= delta_dias <= upper_window:
                return True, row['descricao']
        
        return False, None

# Exemplo de uso
if __name__ == "__main__":
    # Inicializar gerenciador de feriados para 2024-2025
    feriados = FeriadosBrasil(anos=[2024, 2025])
    
    # Mostrar todos os feriados
    print(feriados.feriados[['data', 'descricao', 'tipo']])
    
    # Verificar se uma data é feriado
    e_feriado, descricao = feriados.verificar_feriado("2024-12-25")
    print(f"2024-12-25 é feriado? {e_feriado} - {descricao}")
    
    # Obter ajustes para feriados
    ajustes = feriados.obter_ajustes_feriados()
    print(f"Ajustes para feriados: {ajustes}")
