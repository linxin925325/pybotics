"""Kinematic chain module."""
from itertools import chain, compress
from typing import Any, Sequence, Union, Sized, Optional

import numpy as np  # type: ignore

from pybotics.errors import LinkConventionError, LinkSequenceError, \
    SequenceLengthError
from pybotics.link import Link
from pybotics.link_convention import LinkConvention
from pybotics.revolute_mdh_link import RevoluteMDHLink
from pybotics.validation import is_same_link_conventions, \
    is_sequence_length_correct


class KinematicChain(Sized):
    """
    Assembly of rigid bodies.

    Connected by joints to provide constrained motion.
    """

    def __init__(self, links: Sequence[Link]) -> None:
        """
        Construct a kinematic chain.

        :param links: sequence of links
        """
        self._links = []  # type: Sequence[Link]
        self._optimization_mask = [False] * len(links)

        self.links = links

    def __len__(self) -> int:
        """
        Get the length of the chain.

        :return:
        """
        return len(self.links)

    def apply_optimization_vector(self, vector: np.ndarray) -> None:
        """
        Update the current instance with new optimization parameters.

        :param vector: new parameters to apply
        """
        # we are going to iterate through the given vector;
        # an iterator allows us to next()
        # (aka `pop`) the values only when desired;
        # we only update the current vector where the mask is True
        vector_iterator = iter(vector)
        updated_vector = [v if not m else next(vector_iterator)
                          for v, m in zip(self.vector,
                                          self.optimization_mask)]
        updated_links = self.array_2_links(np.array(updated_vector),
                                           self.convention)
        self.links = updated_links

    @staticmethod
    def array_2_links(array: np.ndarray,
                      convention: LinkConvention) -> Sequence[Link]:
        """
        Generate a sequence of links from a given array of link parameters.

        :param array: link parameters
        :param convention: link convention
        :return: sequence of links
        """
        # create link sequences based on convention;
        # vectors are reshaped to a 2D array based
        # on number of parameters per link
        if convention is LinkConvention.MDH:
            links = [RevoluteMDHLink(*row) for row in
                     array.reshape((-1, LinkConvention.MDH.value))]
        else:
            raise LinkConventionError()

        return links

    @property
    def convention(self) -> LinkConvention:
        """
        Get LinkConvention.

        :return: link convention
        """
        return self.links[0].convention

    @classmethod
    def from_array(cls, array: np.ndarray,
                   convention: LinkConvention) -> Any:
        """
        Generate a kinematic chain from a given array of link parameters.

        :param array: link parameters
        :param convention: link convention
        :return: kinematic chain instance
        """
        return cls(links=cls.array_2_links(array, convention))

    @property
    def links(self) -> Sequence[Link]:
        """
        Get links of the kinematic chain.

        :return: sequence of links
        """
        return self._links

    @links.setter
    def links(self, value: Sequence[Link]) -> None:
        if not is_same_link_conventions(value):
            raise LinkSequenceError()
        self._links = value

    @property
    def num_dof(self) -> int:
        """
        Get number of degrees of freedom.

        :return: number of degrees of freedom
        """
        return len(self)

    @property
    def optimization_mask(self) -> Sequence[bool]:
        """
        Get the mask used to select the optimization parameters.

        :return: mask
        """
        return self._optimization_mask

    @optimization_mask.setter
    def optimization_mask(self,
                          mask: Union[bool, Sequence[bool]]) -> None:
        if isinstance(mask, bool):
            self._optimization_mask = [mask] * len(self.vector)
        else:
            self._optimization_mask = list(mask)

    @property
    def optimization_vector(self) -> np.ndarray:
        """
        Get the values of parameters being optimized.

        :return: optimization parameter values
        """
        filtered_iterator = compress(self.vector, self.optimization_mask)
        optimization_vector = np.array(list(filtered_iterator))
        return optimization_vector

    def transforms(self, position: Optional[Sequence[float]] = None) -> \
            Sequence[np.ndarray]:
        """
        Generate a sequence of spatial transforms.

        The sequence represents the given position of the kinematic chain.
        :param position: given position of kinematic chain
        :return: sequence of transforms
        """
        # validate
        if position is not None:
            if not is_sequence_length_correct(position, self.num_dof):
                raise SequenceLengthError('position', self.num_dof)
        else:
            position = np.zeros(len(self))

        # FIXME: remove type ignore for mypy bugs:
        # error: Argument 2 to "zip" has incompatible type
        # "Optional[Iterable[float]]"; expected "Iterable[float]";
        # error: Call to untyped function "transform"
        # of "Link" in typed context
        transforms = [link.transform(p) for link, p in  # type: ignore
                      zip(self.links, position)]  # type: ignore
        return transforms

    @property
    def vector(self) -> np.ndarray:
        """
        Get the vector representation of the kinematic chain.

        :return: vectorized kinematic chain
        """
        return np.array(list(chain(self.links)))
