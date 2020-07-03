"""
    model
    ~~~~~
"""
from typing import List, Union
import numpy as np
import pandas as pd
from mrtool import MRData, LinearCovModel


class OverallModel:
    """Overall model in charge of fit all location together without
    random effects.
    """

    def __init__(self,
                 data: MRData,
                 cov_models: List[LinearCovModel]):
        """Constructor of OverallModel

        Args:
            data (MRData): Data object from MRTool
            cov_models (List[LinearCovModel]):
                List of linear covariate model from MRTool.
        """
        self.data = data
        self.cov_models = cov_models
        for cov_model in self.cov_models:
            cov_model.attach_data(self.data)

        self.mat = self.create_design_mat()
        self.soln = None

    def create_design_mat(self, data: MRData = None) -> np.ndarray:
        """Create design matrix

        Args:
            data (MRData, optional):
                Create design matrix from the given data object. If ``None`` use
                the attribute ``self.data``. Defaults to None.

        Returns:
            np.ndarray: Design matrix.
        """
        data = self.data if data is None else data
        return np.hstack([cov_model.create_design_mat(data)[0]
                          for cov_model in self.cov_models])

    def fit_model(self):
        """Fit the model
        """
        self.soln = solve_ls(self.mat, self.data.obs, self.data.obs_se)

    def predict(self, data: MRData = None) -> np.ndarray:
        """Predict from fitting result.

        Args:
            data (MRData, optional):
                Given data object to predict, if ``None`` use the attribute
                ``self.data`` Defaults to None.

        Returns:
            np.ndarray: Prediction.
        """
        data = self.data if data is None else data
        mat = self.create_design_mat(data)
        return mat.dot(self.soln)


class StudyModel:
    """Study specific Model.
    """

    def __init__(self, data: MRData, cov_names: List[str]):
        """Constructor of StudyModel

        Args:
            data (MRData): MRTool data object.
            cov_names (List[str]): Covaraite names used in the model.
        """
        self.data = data
        self.cov_names = cov_names
        self.mat = self.create_design_mat()
        self.soln = None

    def create_design_mat(self, data: MRData = None) -> np.ndarray:
        """Create design matrix.

        Args:
            data (MRData, optional):
                Create design matrix from the given data object. If ``None`` use
                the attribute ``self.data``. Defaults to None. Defaults to None.

        Returns:
            np.ndarray: Design matrix.
        """
        data = self.data if data is None else data
        mat = data.get_covs(self.cov_names)

        return mat

    def fit_model(self):
        """Fit the model.
        """
        self.soln = {}
        for study_id in self.data.studies:
            index = self.data.study_id == study_id
            mat = self.mat[index, :]
            obs = self.data.obs[index]
            obs_se = self.data.obs_se[index]
            self.soln[study_id] = solve_ls(mat, obs, obs_se)

    def predict(self, data: MRData = None) -> np.ndarray:
        """Predict from fitting result.

        Args:
            data (MRData, optional):
                Given data object to predict, if ``None`` use the attribute
                ``self.data`` Defaults to None.

        Returns:
            np.ndarray: Prediction.
        """
        data = self.data if data is None else data
        mat = self.mat if data is None else self.create_design_mat(data)

        mean_soln = np.mean(list(self.soln.values()), axis=0)

        soln = np.array([
            self.soln[study_id]
            if study_id in self.data.study_id else mean_soln
            for study_id in data.study_id
        ])

        return np.sum(mat*soln, axis=1)


def solve_ls(mat: np.ndarray,
             obs: np.ndarray, obs_se: np.ndarray) -> np.ndarray:
    """Solve least square problem

    Args:
        mat (np.ndarray): Data matrix
        obs (np.ndarray): Observations
        obs_se (np.ndarray): Observation standard error.

    Returns:
        np.ndarray: Solution.
    """
    v = obs_se**2
    return np.linalg.solve((mat.T/v).dot(mat),
                           (mat.T/v).dot(obs))


def result_to_df(model: Union[OverallModel, StudyModel],
                 prediction: str = 'prediction',
                 residual: str = 'residual') -> pd.DataFrame:
    """Create result data frame.

    Args:
        model (Union[OverallModel, StudyModel]): Model instance.
        prediction (str, optional):
            Column name of the prediction. Defaults to 'prediction'.
        residual (str, optional):
            Column name of the residual. Defaults to 'residual'.

    Returns:
        pd.DataFrame: Result data frame.
    """
    df = model.data.to_df()
    pred = model.predict()
    resi = model.data.obs - pred
    df[prediction] = pred
    df[residual] = resi

    return df
