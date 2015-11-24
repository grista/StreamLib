"""

"""
from streamlib import MurmurHash
import copy
from array import array
from abc import ABCMeta, abstractmethod
from random import randint
from streamlib.utils import doc_inherit
import streamlib.utils as utils
import math




class Sketch(object):
    """
    Interface for Sketch.
    """
    @abstractmethod
    def processBatch(self, *args, **kwargs):
        """
        Summarize data stream in batch mode.
        """
        raise NotImplemented()

    @abstractmethod
    def processItem(self, *args, **kwargs):
        """
        Summarize one item in a data stream.
        """
        raise NotImplemented()

    @abstractmethod
    def estimate(self, *args, **kwargs):
        """
        Estimate properties of given item/key.
        """
        raise NotImplemented()

    @abstractmethod
    def merge(self, *args, **kwargs):
        """
        Merge compatible sketches.
        """
        raise NotImplemented()

    @abstractmethod
    def __add__(self, other):
        return self.merge(other)


class F2(Sketch):
    """
    AMS F2 sketch
    estimate the second moment of the 
    data stream
    """
    def __init__(self, w=20, mu=5, typecode='i'):
        """
        Create a new instance.

        :param w: The number of buckets.
        :type w: int

        :param mu: The number of repeated copies. Used to control the
                   failure probability ~= 2^{-mu}
        :type mu: int

        :param typecode: type to represent the frequencies, check
                         docs.python.org for module `array`
    
        """
        
        self._w = w
        self._mu = mu
        self._sketch = [array(typecode, [0] * w) for i in xrange(mu)]
        self._hashes = [[MurmurHash() for j in xrange(w)] for i in xrange(mu)]
        self._hash = hash(self) 


    def processBatch(self, dataStream, weighted=False):
        """
        Summarize the given data stream.

        :param dataStream: any iterable object with hashable elements. 
                           e.g. a list of integers.
        """

        for item in dataStream:
            self.processItem(item, weighted)

            
    def processItem(self, item, weighted=False):
        """
        Summarize the given data stream, but only process one
        item.

        :param item: hashable object to be processed
                           e.g. an integer
        """
        if not weighted:
            for i in xrange(self._mu):
                for j in xrange(self._w):
                    self._sketch[i][j] += self._hashes[i][j].hash(item) % 2 * 2 - 1
        else:
            itm, wt = item
            for i in xrange(self._mu):
                for j in xrange(self._w):
                    self._sketch[i][j] += (self._hashes[i][j].hash(itm) % 2 * 2 - 1) * wt                                    

    def estimate(self):
        """
        Estimate the F2 moment of the given stream
        
        :return: estimated F2 moment
        :rtype: int/real
        """

        return utils.median([utils.mean( map(lambda x: x**2, self._sketch[i]) )
                             for i in xrange(self._mu)])



    def reproduce(self, num=1):
        """
        Reproduce F2 Sketch instance(s) to have the same
        internal status.

        :param num: number of instances to be reproduced
        :type num: int

        :return: reproduced instance. if num > 1, a list 
                 of instances will be returned
        """
        if type(num) is not int:
            raise TypeError('num should be int')
        if num < 1:
            raise ValueError('num should >= 1')

        if num == 1:
            return copy.deepcopy(self)
        else:
            return [copy.deepcopy(self)]


    def merge(self, other):
        """
        Merge two F2 Sketch instances if they are compatible.

        :param other: an instance of F2 Sketch, 
        """
        if other._hash != self._hash:
            raise ValueError('two instances are not compatible')

        res = F2(w=1, mu=1)
        res._sketch = copy.deepcopy(self._sketch)
        res._hashes = copy.deepcopy(self._hashes)
        res._w = self._w
        res._mu = self._mu
        res._hash = self._hash

        for i in xrange(self._mu):
            for j in xrange(self._w):
                res._sketch[i][j] += other._sketch[i][j]

        return res



class CountSketch(object):
    """
    Count Sketch.
    """
    def __init__(self, w=20, mu=5, typecode='i'):
        """
        Create a new instance.

        :param w: The number of buckets.
        :type w: int

        :param mu: The number of repeated copies. Used to control the
                   failure probability ~= 2^{-mu}
        :type mu: int

        :param typecode: type to represent the frequencies, check
                         docs.python.org for module `array`

        """
        self._w = w
        self._mu = mu
        self._sketch = [array(typecode, [0] * w) for i in xrange(mu)]
        self._sign = [MurmurHash() for i in xrange(mu)]
        self._hashes = [MurmurHash() for i in xrange(mu)]
        self._hash = hash(self) 


    def processBatch(self, dataStream, weighted=False):
        """
        Summarize the given data stream.

        :param dataStream: any iterable object with hashable elements. 
                           e.g. a list of integers.
        :param weighted: if weighted, each item in dataStream should
                         be (key, weight) pair
        """

        for item in dataStream:
            self.processItem(item, weighted)

    def processItem(self, item, weighted=False):
        """
        Summarize the given data stream, but only process one
        item.

        :param item: hashable object to be processed
                           e.g. an integer
        :param weighted: if weighted, item  should
                         be a (key, weight) pair
        """
        if weighted:
            key, weight = item
            for i in xrange(self._mu):
                # where the item is mapped by the i_th hash
                pos = self._hashes[i].hash(key) % self._w
                # increment the bucket
                sg = (self._sign[i].hash(key) % 2) * 2 - 1
                self._sketch[i][pos] += weight * sg
        else:
            for i in xrange(self._mu):
                # where the item is mapped by the i_th hash
                pos = self._hashes[i].hash(item) % self._w
                # increment the bucket
                sg = (self._sign[i].hash(item) % 2) * 2 - 1
                self._sketch[i][pos] += sg
                

    def estimate(self, key):
        """
        Estimate the frequency of given item.

        :param key: key/item in the data stream
        
        :return: estimated frequency of the given key.
        :rtype: int/real
        """
        all_estimators = [(self._sign[i].hash(key) % 2 * 2 - 1) * 
                          self._sketch[i][self._hashes[i].hash(key) % self._w]
                          for i in xrange(self._mu)]
        return utils.median(all_estimators)



    def reproduce(self, num=1):
        """
        Reproduce Count Sketch instance(s) to have the same
        internal status.

        :param num: number of instances to be reproduced
        :type num: int

        :return: reproduced instance. if num > 1, a list 
                 of instances will be returned
        """
        if type(num) is not int:
            raise TypeError('num should be int')
        if num < 1:
            raise ValueError('num should >= 1')

        if num == 1:
            return copy.deepcopy(self)
        else:
            return [copy.deepcopy(self)]


    def merge(self, other):
        """
        Merge two CountSketch instances if they are compatible.

        :param other: an instance of CountSketch, 
        """
        if other._hash != self._hash:
            raise ValueError('two instances are not compatible')

        res = CountSketch(w=1, mu=1)
        res._sketch = copy.deepcopy(self._sketch)
        res._hashes = copy.deepcopy(self._hashes)
        res._sign = copy.deepcopy(self._sign)
        res._w = self._w
        res._mu = self._mu
        res._hash = self._hash

        for i in xrange(self._mu):
            for j in xrange(self._w):
                res._sketch[i][j] += other._sketch[i][j]

        return res


    
    def __add__(self, other):
        return self.merge(other)



class CountMin(Sketch):
    """
    Count-Min sketch.
    support non-negative weighted data stream.
    """
    def __init__(self, w=20, mu=5, typecode='i'):
        """
        Create a new instance.

        :param w: The number of buckets.
        :type w: int

        :param mu: The number of repeated copies. Used to control the
                   failure probability ~= 2^{-mu}
        :type mu: int

        :param typecode: type to represent the frequencies, check
                         docs.python.org for module `array`
        """
        self._w = w
        self._mu = mu
        self._sketch = [array(typecode, [0] * w) for i in xrange(mu)]
        self._hashes = [MurmurHash() for i in xrange(mu)]
        self._hash = hash(self) 

    def processBatch(self, dataStream, weighted=False):
        """
        Summarize the given data stream.

        :param dataStream: any iterable object with hashable elements. 
                           e.g. a list of integers.
        :param weighted: if weighted, each item in dataStream should
                         be (key, weight) pair, where weight > 0
        """

        for item in dataStream:
            self.processItem(item, weighted)

    def processItem(self, item, weighted=False):
        """
        Summarize the given data stream, but only process one
        item.

        :param item: hashable object to be processed
                           e.g. an integer
        :param weighted: if weighted, item  should
                         be a (key, weight) pair, where weight > 0
        """
        if weighted:
            key, weight = item
            for i in xrange(self._mu):
                # where the item is mapped by the i_th hash
                pos = self._hashes[i].hash(key) % self._w
                # increment the bucket
                self._sketch[i][pos] += weight            
        else:
            for i in xrange(self._mu):
                # where the item is mapped by the i_th hash
                pos = self._hashes[i].hash(item) % self._w
                # increment the bucket
                self._sketch[i][pos] += 1


    def estimate(self, key):
        """
        Estimate the frequency of given item.

        :param key: key/item in the data stream
        
        :return: estimated frequency of the given key.
        :rtype: int/real
        """
        all_estimators = [self._sketch[i][self._hashes[i].hash(key) % self._w]
                          for i in xrange(self._mu)]
        return min(all_estimators)



    def reproduce(self, num=1):
        """
        Reproduce CountMin instance(s) to have the same
        internal status.

        :param num: number of instances to be reproduced
        :type num: int

        :return: reproduced instance. if num > 1, a list 
                 of instances will be returned
        """
        if type(num) is not int:
            raise TypeError('num should be int')
        if num < 1:
            raise ValueError('num should >= 1')

        if num == 1:
            return copy.deepcopy(self)
        else:
            return [copy.deepcopy(self)]
            
        


    def merge(self, other):
        """
        Merge two CountMin instances if they are compatible.

        :param other: an instance of CountMin, 
        """
        if other._hash != self._hash:
            raise ValueError('two instances are not compatible')

        res = CountMin(w=1, mu=1)
        res._sketch = copy.deepcopy(self._sketch)
        res._hashes = copy.deepcopy(self._hashes)
        res._w = self._w
        res._mu = self._mu
        for i in xrange(self._mu):
            for j in xrange(self._w):
                res._sketch[i][j] += other._sketch[i][j]

        return res

                
    def __add__(self, other):
        """
        Overload + for self.merge
        """
        return self.merge(other)



class CountMedian(CountMin):
    """
    Count-Median sketch.
    support negative weighted data stream.
    """

    @doc_inherit
    def __init__(self, w=20, mu=5, typecode='i'):
        super(CountMedian, self).__init__(w, mu, typecode)


    
    def processBatch(self, dataStream, weighted=False):
        """
        Summarize the given data stream.

        :param dataStream: any iterable object with hashable elements. 
                           e.g. a list of integers.
        :param weighted: if weighted, each item in dataStream should
                         be (key, weight) pair, weight can be positive
                         or negtive
        """

        for item in dataStream:
            self.processItem(item, weighted)


    def processItem(self, item, weighted=False):
        """
        Summarize the given data stream, but only process one
        item.

        :param item: hashable object to be processed
                           e.g. an integer
        :param weighted: if weighted, item  should
                         be a (key, weight) pair, weight can be postive
                         or negative
        """
        super(CountMedian, self).processItem(item, weighted)


    def estimate(self, key):
        """
        Estimate the frequency of given item.

        :param key: key/item in the data stream
        
        :return: estimated frequency of the given key.
        :rtype: int/real
        """
        all_estimators = [self._sketch[i][self._hashes[i].hash(key) % self._w]
                          for i in xrange(self._mu)]
        return utils.median(all_estimators)

class MG(Sketch):
    """
    Implementation of MG Sketch algorithm. 
    """
    def __init__(self, k):
        """
        Create new instance. 
        :param k: the number of distinct elements in the datastream
        """
        self.A = {}
        self.k = k

    def processBatch(self,dataStream):
        """
        Summarize the given data stream.

        :param dataStream: any iterable object with hashable elements. 
                           e.g. a list of integers.
        """
        for a in dataStream:
            self.processItem(a)

    def processItem(self, item):
        """
        Summarize the given data stream, but only process one
        item.

        :param item: hashable object to be processed
                           e.g. an integer
        """
        if item in self.A.keys():
            self.A[item] += 1 
        elif len(self.A.keys()) < self.k - 1:
            self.A[item] = 1
        else:
            for l in self.A.keys():
                self.A[l] -= 1
                if self.A[l] == 0:
                    del self.A[l]

    def estimate(self, a):
        """
        Provides an estimate of the amount of times a token occurs. 
        :param a: A query 'a' where the value is to be returned if a is in the query.
        """
        if a in self.A.keys():
            return self.A[a]
        else:
            return 0



# class DistinctElement(Sketch):
#     """
#     Computes an epsilon-delta approximation of the distinct elements that 
#     appear in the data stream. 
#     """

#     def __init__(self, delta = 0.01):
#         """
#         Create a new instance.

#         :param z: Holds the maximum value of zeroes h(j)
#         :type: int

#         """

#         self.z = 0 
#         self.h = MurmurHash()
#         self.n_hash = int(math.log(1. / delta))

#         """
#         Summarize the given data stream.

#         :param dataStream: any iterable object with hashable elements. 
#                            e.g. a list of integers.
#         """
    
#     def processBatch(self, dataStream):
#         res = [0 for i in range(self.n_hash)]
#         for item in dataStream:
#             k = dataStream.index(item)
#             self.processItem(item)
#             res[k] = 2**(self.z + 0.5)
#         return utils.median(res)

#         """
#         Summarize the given data stream, but only process one
#         item.

#         :param item: hashable object to be processed
#                            e.g. an integer
#         """
#     def processItem(self,item):
#         hs = utils.zeros(self.h.hash(item))
#         if hs >= self.z:
#             self.z = hs

class DistinctElement(Sketch):

    def __init__(self,w=20, mu=5, typecode = 'i'):
        self.w = w
        self.mu = mu
        self.sketch = [array(typecode, [0] * w) for i in xrange(mu)]
        self.hashes = [MurmurHash() for i in xrange(mu)]
        self.hash = hash(self)

    def processBatch(self, dataStream):
        for item in dataStream:
            self.processItem(item)

    def processItem(self,item):
        for i in xrange(self.mu):
            hs = utils.zeros(self.hashes[i].hash(item) % self.w)
            if hs >= self.sketch[i]:
                self.sketch[i] = hs

    def estimate(self):
        return utils.median([utils.mean(map(lambda z: 2**(z+0.5), self.sketch[i])) for i in xrange(self.mu)])


# class BJKST(Sketch):

#     def __init__(self, thresh):
#         self.h = MurmurHash()
#         self.g = MurmurHash()
#         self.thresh = .01       
#         self.z = 0 
#         self.B = {}
    
#     def processBatch(self, dataStream):
#          for item in dataStream:
#              self.processItem(item)

#     def processItem(self, item):
#         hs = utils.zeros(self.h.hash(item))
#         if hs >= self.z:
#             self.B[self.g.hash(item)] = hs
#             while(len(self.B) >= 1 / self.thresh):
#                 self.z += 1
#                 self.B = {k:v for k, v in self.B.items() if v >= self.z}

#     def estimate(self):
#         return len(self.B)*2**z

class BJKST(Sketch):

    def __init__(self, w=20, mu=5, typecode ='i'):
        self.w = w 
        self.mu = mu
        self.B = {}
        self.sketch = [array(typecode, [0]*w) for i in xrange(mu)]
        self.h_hashes = [MurmurHash() for i in xrange(mu)]
        self.g_hashes = [MurmurHash() for i in xrange (mu)]
        self.hash = hash(self)

    def processBatch(self,dataStream):
        for item in dataStream:
            self.processItem(item)

    def processItem(self, item):
        for i in xrange (self.mu):
            hs = utils.zeros(self.h_hashes[i].hash(item) % self.w)
            if hs >= self.sketch[i]:
                self.B[self.g_hashes[i].hash(item)] = hs #Need to figure out how to hash g within specified range
                while (len(self.B) >= 1 / 0.01): #Placeholder value for now. 
                    self.sketch[i] += 1
                    self.B = {k:v for k, v in self.B.items() if v >= self.sketch[i]}

    def estimate(self):
        return utils.median([utils.mean(map(lambda z: len(self.B)*2**z, self.sketch[i])) for i in xrange(self.mu)])

        
        




